"""
Bias-Aware Screening Service
Performs blind evaluation (without personal data) and full evaluation,
then calculates bias delta to detect potential discrimination.
"""
import json
import re
from typing import Dict, Tuple
import google.generativeai as genai
from app.core.config import settings
from app.models.job import Job


class BiasDetectionService:
    """
    Service to detect potential bias in CV screening by:
    1. Removing/masking personal identifiable information (PII)
    2. Performing blind evaluation without PII
    3. Performing full evaluation with complete CV
    4. Calculating bias delta (score difference)
    5. Analyzing potential bias sources
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
    
    def mask_personal_data(self, cv_text: str, candidate_name: str = None) -> str:
        """
        Remove or mask personal identifiable information from CV
        Removes: names, gender, age, university names, photos references, etc.
        """
        masked_cv = cv_text
        
        # Remove candidate name if provided
        if candidate_name:
            # Replace full name with [CANDIDATE]
            masked_cv = re.sub(
                re.escape(candidate_name), 
                "[CANDIDATE]", 
                masked_cv, 
                flags=re.IGNORECASE
            )
            # Also try first name and last name separately
            name_parts = candidate_name.split()
            for part in name_parts:
                if len(part) > 2:  # Avoid replacing short words
                    masked_cv = re.sub(
                        r'\b' + re.escape(part) + r'\b',
                        "[CANDIDATE]",
                        masked_cv,
                        flags=re.IGNORECASE
                    )
        
        # Mask common name patterns
        masked_cv = re.sub(r'\bName\s*:\s*[^\n]+', 'Name: [CANDIDATE]', masked_cv, flags=re.IGNORECASE)
        masked_cv = re.sub(r'\bFull Name\s*:\s*[^\n]+', 'Full Name: [CANDIDATE]', masked_cv, flags=re.IGNORECASE)
        
        # Mask gender-related terms
        gender_patterns = [
            r'\b(Male|Female|M|F|Non-binary|Gender)\s*:\s*[^\n]+',
            r'\b(Mr\.|Mrs\.|Ms\.|Miss)\s+',
            r'\b(he|she|him|her|his|hers)\b',
        ]
        for pattern in gender_patterns:
            masked_cv = re.sub(pattern, '[REDACTED]', masked_cv, flags=re.IGNORECASE)
        
        # Mask age-related information
        age_patterns = [
            r'\b(Age|DOB|Date of Birth|Born)\s*:\s*[^\n]+',
            r'\b(aged|age)\s+\d+',
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # Dates
        ]
        for pattern in age_patterns:
            masked_cv = re.sub(pattern, '[AGE REDACTED]', masked_cv, flags=re.IGNORECASE)
        
        # Mask university/college names (common patterns)
        # This is tricky - we'll mask institution names but keep degree info
        masked_cv = re.sub(
            r'\b(University|College|Institute|School)\s+of\s+[A-Z][^\n,]+',
            '[EDUCATIONAL INSTITUTION]',
            masked_cv
        )
        masked_cv = re.sub(
            r'\b[A-Z][a-z]+\s+(University|College|Institute)\b',
            '[EDUCATIONAL INSTITUTION]',
            masked_cv
        )
        
        # Remove photo references
        masked_cv = re.sub(r'\b(Photo|Picture|Image)\s*:\s*[^\n]+', '', masked_cv, flags=re.IGNORECASE)
        masked_cv = re.sub(r'\[.*?photo.*?\]', '', masked_cv, flags=re.IGNORECASE)
        
        # Mask nationality/ethnicity
        masked_cv = re.sub(
            r'\b(Nationality|Ethnicity|Race|National)\s*:\s*[^\n]+',
            'Nationality: [REDACTED]',
            masked_cv,
            flags=re.IGNORECASE
        )
        
        # Clean up multiple spaces and newlines
        masked_cv = re.sub(r'\n\s*\n\s*\n', '\n\n', masked_cv)
        masked_cv = re.sub(r'  +', ' ', masked_cv)
        
        return masked_cv.strip()
    
    def evaluate_cv(self, cv_text: str, job: Job, is_blind: bool = False) -> Dict:
        """
        Evaluate CV using Gemini AI
        
        Args:
            cv_text: CV content (masked if blind evaluation)
            job: Job object with requirements
            is_blind: Whether this is a blind evaluation
            
        Returns:
            dict with score, summary, strengths, weaknesses
        """
        evaluation_type = "BLIND" if is_blind else "FULL"
        blind_note = """
        
**IMPORTANT**: This is a BLIND evaluation. The personal information has been masked.
Focus ONLY on:
- Technical skills and competencies
- Work experience and achievements (without institution names)
- Project descriptions and outcomes
- Demonstrated abilities and knowledge

DO NOT consider or infer:
- Gender, age, or nationality
- Specific university prestige
- Personal characteristics
""" if is_blind else ""
        
        prompt = f"""You are conducting a {evaluation_type} CV evaluation for hiring.

JOB DETAILS:
Title: {job.title}
Department: {job.department or 'Not specified'}
Experience Required: {job.min_experience_years}-{job.max_experience_years} years
Level: {job.experience_level or 'Not specified'}

JOB REQUIREMENTS:
{job.requirements}

CANDIDATE CV:
{cv_text[:8000]}
{blind_note}

Provide an objective evaluation with:
1. SCORE (0-100): Based purely on skills, experience, and achievements
2. SUMMARY: Brief assessment of candidate's qualifications
3. STRENGTHS: Key relevant qualifications
4. WEAKNESSES: Missing or weak areas

Respond in JSON format:
{{
    "score": <number>,
    "summary": "<text>",
    "strengths": "<text>",
    "weaknesses": "<text>"
}}

Be objective and fair. Focus on demonstrable skills and experience only."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            result = json.loads(response_text)
            result["score"] = float(result.get("score", 0))
            return result
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            return {
                "score": 0,
                "summary": f"Error during evaluation: {str(e)}",
                "strengths": "",
                "weaknesses": ""
            }
    
    def perform_bias_analysis(
        self,
        cv_text: str,
        job: Job,
        candidate_name: str = None
    ) -> Dict:
        """
        Perform complete bias-aware analysis:
        1. Mask personal data
        2. Blind evaluation
        3. Full evaluation
        4. Calculate bias delta
        5. Analyze differences
        
        Returns:
            {
                "masked_cv": str,
                "blind_score": float,
                "blind_evaluation": dict,
                "full_score": float,
                "full_evaluation": dict,
                "bias_delta": float,
                "bias_analysis": dict
            }
        """
        # Step 1: Mask personal data
        masked_cv = self.mask_personal_data(cv_text, candidate_name)
        
        # Step 2: Blind evaluation
        print("  🔍 Performing blind evaluation (no personal data)...")
        blind_eval = self.evaluate_cv(masked_cv, job, is_blind=True)
        blind_score = blind_eval.get("score", 0)
        
        # Step 3: Full evaluation
        print("  👁️ Performing full evaluation (with personal data)...")
        full_eval = self.evaluate_cv(cv_text, job, is_blind=False)
        full_score = full_eval.get("score", 0)
        
        # Step 4: Calculate bias delta
        bias_delta = full_score - blind_score
        
        # Step 5: Analyze bias
        bias_analysis = self._analyze_bias(blind_score, full_score, bias_delta)
        
        print(f"  📊 Bias Analysis: Blind={blind_score}%, Full={full_score}%, Delta={bias_delta:+.1f}%")
        
        return {
            "masked_cv": masked_cv,
            "blind_score": blind_score,
            "blind_evaluation": blind_eval,
            "full_score": full_score,
            "full_evaluation": full_eval,
            "bias_delta": bias_delta,
            "bias_analysis": bias_analysis
        }
    
    def _analyze_bias(self, blind_score: float, full_score: float, delta: float) -> Dict:
        """
        Analyze the bias delta and provide interpretation
        """
        analysis = {
            "blind_score": blind_score,
            "full_score": full_score,
            "bias_delta": delta,
            "bias_detected": False,
            "bias_direction": "none",
            "bias_severity": "none",
            "interpretation": "",
            "recommendation": ""
        }
        
        # Determine bias severity
        abs_delta = abs(delta)
        
        if abs_delta < 3:
            analysis["bias_severity"] = "negligible"
            analysis["interpretation"] = "Very minimal difference between blind and full evaluation. No significant bias detected."
            analysis["recommendation"] = "Proceed with confidence. Evaluation appears objective."
        elif abs_delta < 7:
            analysis["bias_severity"] = "low"
            analysis["bias_detected"] = False
            analysis["interpretation"] = "Small difference detected, likely due to normal variation in evaluation."
            analysis["recommendation"] = "No major concern. Consider using blind score for fairness."
        elif abs_delta < 12:
            analysis["bias_severity"] = "moderate"
            analysis["bias_detected"] = True
            analysis["interpretation"] = "Moderate bias detected. Personal information may have influenced scoring."
            analysis["recommendation"] = "⚠️ Review this candidate's evaluation. Consider blind score or re-evaluate."
        else:
            analysis["bias_severity"] = "high"
            analysis["bias_detected"] = True
            analysis["interpretation"] = "Significant bias detected! Strong influence from personal data."
            analysis["recommendation"] = "🚨 ALERT: Use blind score only. High risk of biased decision."
        
        # Determine bias direction
        if delta > 3:
            analysis["bias_direction"] = "positive"
            analysis["interpretation"] += " Personal data increased the score (positive bias)."
        elif delta < -3:
            analysis["bias_direction"] = "negative"
            analysis["interpretation"] += " Personal data decreased the score (negative bias)."
        
        return analysis


# Singleton instance
bias_detection_service = BiasDetectionService()
