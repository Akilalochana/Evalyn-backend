"""
Project-Based Evaluation Service
Evaluates candidate's GitHub repositories or uploaded projects
to assess code quality, architecture, and practical skills.
"""
import json
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
import google.generativeai as genai
from app.core.config import settings


class ProjectEvaluator:
    """
    Service to evaluate candidate projects:
    1. Clone/extract GitHub repositories
    2. Analyze code structure and quality
    3. Evaluate architecture and best practices
    4. Generate project score and feedback
    5. Combine with CV score for final ranking
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
        self.project_base_dir = "uploads/projects"
        os.makedirs(self.project_base_dir, exist_ok=True)
    
    def clone_github_repo(self, github_url: str, destination: str) -> bool:
        """
        Clone a GitHub repository to local directory
        
        Args:
            github_url: GitHub repository URL
            destination: Local path to clone to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate GitHub URL
            if not re.match(r'https?://github\.com/[\w-]+/[\w-]+', github_url):
                print(f"Invalid GitHub URL: {github_url}")
                return False
            
            # Clone repo
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', github_url, destination],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✓ Successfully cloned {github_url}")
                return True
            else:
                print(f"Error cloning repo: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Git clone timeout")
            return False
        except FileNotFoundError:
            print("Git is not installed or not in PATH")
            return False
        except Exception as e:
            print(f"Error cloning repository: {e}")
            return False
    
    def analyze_project_structure(self, project_path: str) -> Dict:
        """
        Analyze project directory structure
        
        Returns:
            {
                "total_files": int,
                "total_lines": int,
                "file_types": {...},
                "has_readme": bool,
                "has_tests": bool,
                "has_ci_cd": bool,
                "technologies_detected": [...],
                "structure_summary": str
            }
        """
        if not os.path.exists(project_path):
            return {}
        
        analysis = {
            "total_files": 0,
            "total_lines": 0,
            "file_types": {},
            "has_readme": False,
            "has_tests": False,
            "has_ci_cd": False,
            "technologies_detected": [],
            "folders": []
        }
        
        # Walk through project directory
        for root, dirs, files in os.walk(project_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__', '.pytest_cache']]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_lower = file.lower()
                
                # Count files
                analysis["total_files"] += 1
                
                # Check for key files
                if file_lower in ['readme.md', 'readme.txt', 'readme']:
                    analysis["has_readme"] = True
                
                if 'test' in file_lower or file_lower.startswith('test_'):
                    analysis["has_tests"] = True
                
                if file_lower in ['.github', '.gitlab-ci.yml', 'jenkinsfile', '.travis.yml']:
                    analysis["has_ci_cd"] = True
                
                # Track file types
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
                
                # Count lines in code files
                if ext in ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.rb', '.go', '.rs', '.ts', '.jsx', '.tsx']:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            analysis["total_lines"] += sum(1 for _ in f)
                    except:
                        pass
            
            # Track folder structure
            rel_path = os.path.relpath(root, project_path)
            if rel_path != '.':
                analysis["folders"].append(rel_path)
        
        # Detect technologies
        analysis["technologies_detected"] = self._detect_technologies(analysis["file_types"], project_path)
        
        return analysis
    
    def _detect_technologies(self, file_types: Dict, project_path: str) -> List[str]:
        """Detect technologies based on file types and config files"""
        technologies = []
        
        # Language detection
        if '.py' in file_types:
            technologies.append("Python")
        if '.js' in file_types or '.jsx' in file_types:
            technologies.append("JavaScript")
        if '.ts' in file_types or '.tsx' in file_types:
            technologies.append("TypeScript")
        if '.java' in file_types:
            technologies.append("Java")
        if '.cpp' in file_types or '.c' in file_types:
            technologies.append("C/C++")
        if '.cs' in file_types:
            technologies.append("C#")
        if '.go' in file_types:
            technologies.append("Go")
        if '.rs' in file_types:
            technologies.append("Rust")
        
        # Framework detection
        config_files = {}
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file in ['requirements.txt', 'package.json', 'pom.xml', 'build.gradle', 'Cargo.toml', 'go.mod']:
                    file_path = os.path.join(root, file)
                    config_files[file] = file_path
        
        if 'requirements.txt' in config_files:
            try:
                with open(config_files['requirements.txt'], 'r') as f:
                    content = f.read().lower()
                    if 'django' in content:
                        technologies.append("Django")
                    if 'flask' in content:
                        technologies.append("Flask")
                    if 'fastapi' in content:
                        technologies.append("FastAPI")
            except:
                pass
        
        if 'package.json' in config_files:
            try:
                with open(config_files['package.json'], 'r') as f:
                    content = f.read().lower()
                    if 'react' in content:
                        technologies.append("React")
                    if 'vue' in content:
                        technologies.append("Vue")
                    if 'angular' in content:
                        technologies.append("Angular")
                    if 'express' in content:
                        technologies.append("Express")
                    if 'next' in content:
                        technologies.append("Next.js")
            except:
                pass
        
        return technologies
    
    def extract_code_samples(self, project_path: str, max_files: int = 5) -> List[Dict]:
        """
        Extract code samples from key files for AI evaluation
        
        Returns:
            List of {filename, content, language}
        """
        samples = []
        
        # Prioritize main files
        priority_patterns = [
            'main.py', 'app.py', 'server.py', 'index.js', 'app.js', 'main.java',
            'main.go', 'main.rs', 'Program.cs'
        ]
        
        code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.ts', '.jsx', '.tsx']
        
        collected_files = []
        
        # First, look for priority files
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__']]
            
            for file in files:
                if file.lower() in priority_patterns:
                    file_path = os.path.join(root, file)
                    collected_files.insert(0, file_path)  # Add to front
                elif os.path.splitext(file)[1] in code_extensions:
                    file_path = os.path.join(root, file)
                    collected_files.append(file_path)
        
        # Extract content from files
        for file_path in collected_files[:max_files]:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content) > 0:
                        samples.append({
                            "filename": os.path.basename(file_path),
                            "content": content[:2000],  # Limit to 2000 chars per file
                            "language": os.path.splitext(file_path)[1][1:]  # Remove dot
                        })
            except:
                pass
        
        return samples
    
    def evaluate_project_with_ai(
        self,
        project_analysis: Dict,
        code_samples: List[Dict],
        job_title: str
    ) -> Dict:
        """
        Use Gemini AI to evaluate project quality
        
        Returns:
            {
                "project_score": float (0-100),
                "code_quality_score": float (0-100),
                "feedback": str,
                "strengths": str,
                "improvements": str,
                "architecture_rating": str,
                "best_practices_rating": str
            }
        """
        # Build context
        project_summary = f"""
PROJECT ANALYSIS:
- Total Files: {project_analysis.get('total_files', 0)}
- Lines of Code: {project_analysis.get('total_lines', 0)}
- Technologies: {', '.join(project_analysis.get('technologies_detected', []))}
- Has README: {project_analysis.get('has_readme', False)}
- Has Tests: {project_analysis.get('has_tests', False)}
- Has CI/CD: {project_analysis.get('has_ci_cd', False)}
"""
        
        code_context = "\n\n".join([
            f"FILE: {sample['filename']} ({sample['language']})\n```{sample['language']}\n{sample['content']}\n```"
            for sample in code_samples[:3]
        ])
        
        prompt = f"""You are evaluating a candidate's project for a {job_title} position.

{project_summary}

CODE SAMPLES:
{code_context}

Evaluate this project on:
1. CODE QUALITY (0-100): Clean code, readability, organization
2. ARCHITECTURE (0-100): Project structure, design patterns, modularity
3. BEST PRACTICES (0-100): Documentation, testing, error handling, security
4. TECHNICAL DEPTH (0-100): Complexity, algorithms, problem-solving
5. OVERALL PROJECT SCORE (0-100): Weighted average

Provide detailed evaluation:

Respond in JSON format:
{{
    "code_quality_score": <number>,
    "architecture_score": <number>,
    "best_practices_score": <number>,
    "technical_depth_score": <number>,
    "overall_project_score": <number>,
    "strengths": "<bullet points>",
    "improvements": "<bullet points>",
    "architecture_rating": "<Excellent/Good/Average/Poor>",
    "best_practices_rating": "<Excellent/Good/Average/Poor>",
    "feedback": "<detailed paragraph>"
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
            
            # Ensure numeric scores
            result["project_score"] = float(result.get("overall_project_score", 0))
            result["code_quality_score"] = float(result.get("code_quality_score", 0))
            
            return result
            
        except Exception as e:
            print(f"AI evaluation error: {e}")
            return {
                "project_score": 50,
                "code_quality_score": 50,
                "feedback": f"Error during evaluation: {str(e)}",
                "strengths": "Could not analyze",
                "improvements": "Could not analyze",
                "architecture_rating": "Unknown",
                "best_practices_rating": "Unknown"
            }
    
    def evaluate_github_project(
        self,
        github_url: str,
        job_title: str,
        application_id: int
    ) -> Dict:
        """
        Complete evaluation of a GitHub project
        
        Returns:
            {
                "project_score": float,
                "code_quality_score": float,
                "project_analysis": {...},
                "project_feedback": str,
                "project_path": str
            }
        """
        # Create destination directory
        project_dir = os.path.join(
            self.project_base_dir,
            f"app_{application_id}_{Path(github_url).stem}"
        )
        
        print(f"  📦 Cloning repository: {github_url}")
        
        # Clone repository
        if not self.clone_github_repo(github_url, project_dir):
            return {
                "project_score": 0,
                "code_quality_score": 0,
                "project_feedback": "Failed to clone GitHub repository",
                "project_path": None
            }
        
        print("  🔍 Analyzing project structure...")
        project_analysis = self.analyze_project_structure(project_dir)
        
        print("  📝 Extracting code samples...")
        code_samples = self.extract_code_samples(project_dir)
        
        print("  🤖 AI evaluation in progress...")
        ai_evaluation = self.evaluate_project_with_ai(
            project_analysis,
            code_samples,
            job_title
        )
        
        print(f"  ✓ Project Score: {ai_evaluation['project_score']:.0f}%")
        
        return {
            "project_score": ai_evaluation["project_score"],
            "code_quality_score": ai_evaluation.get("code_quality_score", 0),
            "project_analysis": {
                **project_analysis,
                **ai_evaluation
            },
            "project_feedback": ai_evaluation["feedback"],
            "project_path": project_dir
        }
    
    def calculate_composite_score(
        self,
        cv_score: float,
        project_score: float,
        cv_weight: float = 0.6,
        project_weight: float = 0.4
    ) -> float:
        """
        Calculate final composite score combining CV and project evaluation
        
        Args:
            cv_score: Score from CV evaluation (0-100)
            project_score: Score from project evaluation (0-100)
            cv_weight: Weight for CV score (default 60%)
            project_weight: Weight for project score (default 40%)
            
        Returns:
            Weighted composite score (0-100)
        """
        composite = (cv_score * cv_weight) + (project_score * project_weight)
        return round(composite, 2)


# Singleton instance
project_evaluator = ProjectEvaluator()
