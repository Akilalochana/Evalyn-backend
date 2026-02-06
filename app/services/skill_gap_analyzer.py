"""
Skill-Gap Detection Service
Compares job requirements with candidate skills,
identifies missing/weak skills, and generates feedback.
"""
import json
import re
from typing import Dict, List, Set, Tuple
import google.generativeai as genai
from app.core.config import settings
from app.models.job import Job


class SkillGapAnalyzer:
    """
    Service to analyze skill gaps between job requirements and candidate qualifications.
    Provides:
    1. Required skills extraction from job description
    2. Candidate skills extraction from CV
    3. Matching, missing, and weak skills identification
    4. Skill match percentage calculation
    5. Personalized feedback for candidates
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
    
    def extract_job_skills(self, job: Job) -> List[str]:
        """
        Extract required skills from job description and requirements using AI
        
        Returns:
            List of required skills
        """
        prompt = f"""Extract ALL technical skills, tools, technologies, and qualifications required for this job.

JOB TITLE: {job.title}
DEPARTMENT: {job.department or 'Not specified'}
EXPERIENCE LEVEL: {job.experience_level or 'Not specified'}

JOB DESCRIPTION:
{job.description}

REQUIREMENTS:
{job.requirements}

RESPONSIBILITIES:
{job.responsibilities or 'Not specified'}

Extract and categorize ALL skills mentioned or implied. Include:
- Programming languages (e.g., Python, Java)
- Frameworks & libraries (e.g., FastAPI, React)
- Tools & platforms (e.g., Docker, AWS, Git)
- Databases (e.g., PostgreSQL, MongoDB)
- Methodologies (e.g., Agile, TDD)
- Soft skills (e.g., Communication, Leadership)
- Certifications (e.g., AWS Certified)
- Domain knowledge (e.g., Machine Learning, DevOps)

Respond in JSON format:
{{
    "technical_skills": ["skill1", "skill2", ...],
    "tools_platforms": ["tool1", "tool2", ...],
    "soft_skills": ["skill1", "skill2", ...],
    "certifications": ["cert1", "cert2", ...],
    "domain_knowledge": ["domain1", "domain2", ...]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            result = json.loads(response_text)
            
            # Flatten all skills into a single list
            all_skills = []
            for category, skills in result.items():
                all_skills.extend(skills)
            
            return all_skills
            
        except Exception as e:
            print(f"Error extracting job skills: {e}")
            # Fallback: simple keyword extraction
            return self._fallback_skill_extraction(job)
    
    def _fallback_skill_extraction(self, job: Job) -> List[str]:
        """Simple fallback skill extraction using keywords"""
        text = f"{job.requirements} {job.description} {job.responsibilities or ''}"
        
        # Common skill patterns
        common_skills = [
            "Python", "Java", "JavaScript", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin",
            "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI", "Spring",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "Git",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "Machine Learning", "AI", "DevOps", "Agile", "Scrum", "REST API"
        ]
        
        found_skills = []
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.append(skill)
        
        return found_skills
    
    def extract_candidate_skills(self, cv_text: str) -> List[str]:
        """
        Extract candidate's skills from CV using AI
        
        Returns:
            List of candidate skills
        """
        prompt = f"""Extract ALL skills, technologies, tools, and qualifications mentioned in this candidate's CV.

CANDIDATE CV:
{cv_text[:8000]}

Extract everything the candidate mentions having experience with. Include:
- Programming languages they've used
- Frameworks, libraries, tools
- Technologies and platforms
- Certifications held
- Methodologies practiced
- Domain expertise areas
- Soft skills demonstrated

Respond in JSON format:
{{
    "technical_skills": ["skill1", "skill2", ...],
    "tools_platforms": ["tool1", "tool2", ...],
    "soft_skills": ["skill1", "skill2", ...],
    "certifications": ["cert1", "cert2", ...],
    "domain_knowledge": ["domain1", "domain2", ...],
    "years_of_experience": {{
        "skill1": "X years",
        "skill2": "Y years"
    }}
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            result = json.loads(response_text)
            
            # Flatten all skills
            all_skills = []
            for category, value in result.items():
                if category != "years_of_experience" and isinstance(value, list):
                    all_skills.extend(value)
            
            return all_skills
            
        except Exception as e:
            print(f"Error extracting candidate skills: {e}")
            return []
    
    def analyze_skill_gaps(
        self,
        required_skills: List[str],
        candidate_skills: List[str]
    ) -> Dict:
        """
        Compare required vs candidate skills and identify gaps
        
        Returns:
            {
                "matched_skills": [...],
                "missing_skills": [...],
                "extra_skills": [...],
                "match_percentage": float,
                "gap_analysis": {...}
            }
        """
        # Normalize skills for comparison (case-insensitive)
        required_set = {skill.lower().strip() for skill in required_skills}
        candidate_set = {skill.lower().strip() for skill in candidate_skills}
        
        # Find matches (fuzzy matching for similar terms)
        matched = []
        missing = []
        
        for req_skill in required_skills:
            found = False
            for cand_skill in candidate_skills:
                if self._skills_match(req_skill, cand_skill):
                    matched.append(req_skill)
                    found = True
                    break
            if not found:
                missing.append(req_skill)
        
        # Find extra skills candidate has
        extra = []
        for cand_skill in candidate_skills:
            found = False
            for req_skill in required_skills:
                if self._skills_match(cand_skill, req_skill):
                    found = True
                    break
            if not found:
                extra.append(cand_skill)
        
        # Calculate match percentage
        if len(required_skills) > 0:
            match_percentage = (len(matched) / len(required_skills)) * 100
        else:
            match_percentage = 0
        
        return {
            "matched_skills": matched,
            "missing_skills": missing,
            "extra_skills": extra[:10],  # Limit to top 10 extra skills
            "match_percentage": round(match_percentage, 1),
            "total_required": len(required_skills),
            "total_matched": len(matched),
            "total_missing": len(missing)
        }
    
    def _skills_match(self, skill1: str, skill2: str) -> bool:
        """Check if two skills match (fuzzy matching)"""
        s1 = skill1.lower().strip()
        s2 = skill2.lower().strip()
        
        # Exact match
        if s1 == s2:
            return True
        
        # One contains the other
        if s1 in s2 or s2 in s1:
            return True
        
        # Common aliases
        aliases = {
            "javascript": ["js", "ecmascript"],
            "python": ["py"],
            "postgresql": ["postgres", "psql"],
            "kubernetes": ["k8s"],
            "docker": ["containerization"],
            "aws": ["amazon web services"],
            "gcp": ["google cloud platform", "google cloud"],
            "azure": ["microsoft azure"],
        }
        
        for key, vals in aliases.items():
            if (s1 == key and s2 in vals) or (s2 == key and s1 in vals):
                return True
            if (s1 in vals and s2 == key) or (s2 in vals and s1 == key):
                return True
        
        return False
    
    def generate_feedback(
        self,
        candidate_name: str,
        job_title: str,
        gap_analysis: Dict
    ) -> str:
        """
        Generate personalized feedback for candidate about skill gaps
        
        Args:
            candidate_name: Candidate's name
            job_title: Position they applied for
            gap_analysis: Result from analyze_skill_gaps
            
        Returns:
            Formatted feedback text
        """
        matched = gap_analysis["matched_skills"]
        missing = gap_analysis["missing_skills"]
        extra = gap_analysis["extra_skills"]
        match_pct = gap_analysis["match_percentage"]
        
        feedback = f"""Dear {candidate_name},

Thank you for your interest in the {job_title} position. We have completed a detailed analysis of your qualifications.

📊 SKILL MATCH OVERVIEW:
Your profile matches {match_pct:.0f}% of the required skills for this role.
- Skills Matched: {len(matched)} out of {gap_analysis['total_required']} required
- Skills to Develop: {len(missing)}

"""
        
        if matched:
            feedback += f"""✅ STRENGTHS - Skills You Have:
"""
            for i, skill in enumerate(matched[:15], 1):  # Top 15
                feedback += f"{i}. {skill}\n"
            if len(matched) > 15:
                feedback += f"   ... and {len(matched) - 15} more\n"
            feedback += "\n"
        
        if missing:
            feedback += f"""⚠️ SKILL GAPS - Areas for Development:
To strengthen your candidacy for this role, consider developing these skills:

"""
            for i, skill in enumerate(missing[:15], 1):  # Top 15
                feedback += f"{i}. {skill}\n"
            if len(missing) > 15:
                feedback += f"   ... and {len(missing) - 15} more\n"
            feedback += "\n"
            
            feedback += """💡 RECOMMENDATIONS:
- Consider online courses or certifications in the missing skill areas
- Work on personal projects to gain hands-on experience
- Contribute to open-source projects related to these technologies
- Update your CV once you've acquired these skills and reapply

"""
        
        if extra:
            feedback += f"""🌟 ADDITIONAL STRENGTHS:
You also have valuable skills that go beyond the basic requirements:
"""
            for skill in extra[:10]:
                feedback += f"• {skill}\n"
            feedback += "\n"
        
        # Overall assessment
        if match_pct >= 80:
            feedback += """✨ OVERALL ASSESSMENT:
Your skill set is a strong match for this position. We encourage you to proceed with the application process.
"""
        elif match_pct >= 60:
            feedback += """📈 OVERALL ASSESSMENT:
Your profile shows good potential for this role. Addressing the skill gaps identified above would significantly strengthen your candidacy.
"""
        else:
            feedback += """📚 OVERALL ASSESSMENT:
While we appreciate your interest, there are significant skill gaps for this particular role. We encourage you to develop the missing skills and consider reapplying in the future. Your additional strengths may be better suited for other positions.
"""
        
        feedback += """
Best regards,
HR Team

---
This is an automated skills assessment report. For questions, please contact our HR department.
"""
        
        return feedback
    
    def perform_complete_analysis(
        self,
        cv_text: str,
        job: Job,
        candidate_name: str
    ) -> Dict:
        """
        Perform complete skill-gap analysis
        
        Returns:
            {
                "required_skills": [...],
                "candidate_skills": [...],
                "matched_skills": [...],
                "missing_skills": [...],
                "extra_skills": [...],
                "weak_skills": [...],
                "skill_match_percentage": float,
                "feedback": str
            }
        """
        print("  🔍 Extracting required skills from job...")
        required_skills = self.extract_job_skills(job)
        
        print("  📄 Extracting candidate skills from CV...")
        candidate_skills = self.extract_candidate_skills(cv_text)
        
        print("  📊 Analyzing skill gaps...")
        gap_analysis = self.analyze_skill_gaps(required_skills, candidate_skills)
        
        print("  💬 Generating personalized feedback...")
        feedback = self.generate_feedback(
            candidate_name,
            job.title,
            gap_analysis
        )
        
        # Identify weak skills (mentioned but not strong)
        weak_skills = self._identify_weak_skills(cv_text, gap_analysis["matched_skills"])
        
        print(f"  ✓ Match: {gap_analysis['match_percentage']:.0f}% ({len(gap_analysis['matched_skills'])}/{len(required_skills)} skills)")
        
        return {
            "required_skills": required_skills,
            "candidate_skills": candidate_skills,
            "matched_skills": gap_analysis["matched_skills"],
            "missing_skills": gap_analysis["missing_skills"],
            "extra_skills": gap_analysis["extra_skills"],
            "weak_skills": weak_skills,
            "skill_match_percentage": gap_analysis["match_percentage"],
            "feedback": feedback
        }
    
    def _identify_weak_skills(self, cv_text: str, matched_skills: List[str]) -> List[str]:
        """
        Identify skills that are mentioned but may not be strong
        (e.g., mentioned once, no projects, limited experience)
        """
        weak = []
        cv_lower = cv_text.lower()
        
        for skill in matched_skills:
            skill_lower = skill.lower()
            # Count occurrences
            count = cv_lower.count(skill_lower)
            
            # If mentioned only once or twice, might be weak
            if count <= 2:
                weak.append(skill)
        
        return weak[:10]  # Return top 10 potentially weak skills


# Singleton instance
skill_gap_analyzer = SkillGapAnalyzer()
