import csv
import json
import re
import io
import fitz  # PyMuPDF
import docx
from typing import List
from app.schemas_v3 import QuestionItem

class IntakeParserAgent:
    def __init__(self):
        # Known column headers for CSV parsing
        self.question_headers = ["question", "control id", "question text", "requirement"]
        self.domain_headers = ["domain", "category", "section"]
        self.response_type_headers = ["response type", "type", "format"]

    def parse_questionnaire(self, filename: str, content: bytes) -> List[QuestionItem]:
        ext = filename.split('.')[-1].lower()
        if ext == 'csv':
            return self._parse_csv(content)
        elif ext == 'json':
            return self._parse_json(content)
        elif ext == 'docx':
            return self._parse_docx(content)
        elif ext == 'pdf':
            return self._parse_pdf(content)
        else:
            raise ValueError(f"Unsupported questionnaire format: {ext}")

    def _detect_framework(self, questions: List[QuestionItem]) -> str:
        sig_core_count = 0
        sig_lite_count = 0
        caiq_count = 0
        
        for q in questions:
            if re.match(r'^SIG', q.question_id, re.IGNORECASE) or re.match(r'^[A-Z]\.\d+\.\d+', q.question_id):
                sig_core_count += 1
            if re.match(r'^CAIQ|^\w{3}-\d+', q.question_id, re.IGNORECASE):
                caiq_count += 1
                
        if caiq_count > 50:
            return "caiq"
        elif sig_core_count > 200:
            return "sig_core"
        elif sig_core_count > 50:
            return "sig_lite"
        else:
            return "custom"

    def _infer_response_type(self, text: str) -> str:
        text_lower = text.lower()
        if any(text_lower.startswith(prefix) for prefix in ["do you", "is there", "are there", "does the", "can you", "has the"]):
            return "boolean"
        return "narrative"

    def _parse_csv(self, content: bytes) -> List[QuestionItem]:
        decoded = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
        
        headers = [h.lower().strip() for h in reader.fieldnames] if reader.fieldnames else []
        
        q_col = next((h for h in headers if any(qh in h for qh in self.question_headers)), None)
        id_col = next((h for h in headers if "id" in h), None)
        d_col = next((h for h in headers if any(dh in h for dh in self.domain_headers)), None)
        
        if not q_col:
            q_col = reader.fieldnames[0] # fallback to first column
            
        questions = []
        for i, row in enumerate(reader):
            # mapping original case headers back
            row_lower = {k.lower().strip() if k else "": v for k, v in row.items()}
            q_text = row_lower.get(q_col, "").strip()
            if not q_text:
                continue
                
            q_id = row_lower.get(id_col, f"Q{i+1}") if id_col else f"Q{i+1}"
            domain = row_lower.get(d_col, "") if d_col else ""
            
            q = QuestionItem(
                question_id=q_id,
                domain=domain,
                question_text=q_text,
                response_type=self._infer_response_type(q_text)
            )
            questions.append(q)
            
        framework = self._detect_framework(questions)
        for q in questions:
            q.framework = framework
        return questions

    def _parse_json(self, content: bytes) -> List[QuestionItem]:
        data = json.loads(content)
        questions = []
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "questions" in data:
            items = data["questions"]
        else:
            items = [data]
            
        for i, item in enumerate(items):
            q_text = item.get("question", item.get("question_text", item.get("text", "")))
            if not q_text:
                continue
            q_id = str(item.get("id", item.get("question_id", f"Q{i+1}")))
            domain = item.get("domain", item.get("category", ""))
            resp_type = item.get("response_type", self._infer_response_type(q_text))
            
            q = QuestionItem(
                question_id=q_id,
                domain=domain,
                question_text=q_text,
                response_type=resp_type if resp_type in ["boolean", "narrative", "multiple_choice", "evidence_upload"] else self._infer_response_type(q_text),
                options=item.get("options", [])
            )
            questions.append(q)
            
        framework = self._detect_framework(questions)
        for q in questions:
            q.framework = framework
        return questions

    def _parse_docx(self, content: bytes) -> List[QuestionItem]:
        doc = docx.Document(io.BytesIO(content))
        questions = []
        current_domain = ""
        
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
                
            # Heuristics for domain headers (e.g. "A. Access Control" or heading styles)
            if para.style.name.startswith('Heading') or re.match(r'^[A-Z]\.\s+[A-Z]', text):
                current_domain = text
                continue
                
            if text.endswith('?') or len(text.split()) > 5:
                # Treat as question
                # try to extract ID
                match = re.match(r'^([A-Z0-9\.\-]+)\s+(.*)', text)
                if match:
                    q_id = match.group(1)
                    q_text = match.group(2)
                else:
                    q_id = f"Q{len(questions)+1}"
                    q_text = text
                    
                q = QuestionItem(
                    question_id=q_id,
                    domain=current_domain,
                    question_text=q_text,
                    response_type=self._infer_response_type(q_text)
                )
                questions.append(q)
                
        framework = self._detect_framework(questions)
        for q in questions:
            q.framework = framework
        return questions

    def _parse_pdf(self, content: bytes) -> List[QuestionItem]:
        doc = fitz.open(stream=content, filetype="pdf")
        questions = []
        current_domain = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if re.match(r'^[A-Z]\.\s+[A-Z]', line) and len(line.split()) < 10:
                    current_domain = line
                    continue
                    
                if line.endswith('?') or len(line.split()) > 5:
                    match = re.match(r'^([A-Z0-9\.\-]+)\s+(.*)', line)
                    if match:
                        q_id = match.group(1)
                        q_text = match.group(2)
                    else:
                        q_id = f"Q{len(questions)+1}"
                        q_text = line
                        
                    q = QuestionItem(
                        question_id=q_id,
                        domain=current_domain,
                        question_text=q_text,
                        response_type=self._infer_response_type(q_text)
                    )
                    questions.append(q)
                    
        framework = self._detect_framework(questions)
        for q in questions:
            q.framework = framework
        return questions
