# CV Matching System with Google Gemini

This system automatically analyzes CVs submitted through your career page, matches them against job descriptions, and provides a percentage score for each candidate. **Candidates scoring 75% or above are automatically selected.**

## 🚀 Key Features

- **AI-Powered CV Analysis**: Uses Google's Gemini AI to analyze CVs against job requirements
- **Smart Matching**: Calculates match percentage (0-100%) based on skills, experience, and qualifications
- **Automatic Selection**: Candidates with 75% or above are automatically shortlisted
- **Detailed Insights**: Provides strengths, weaknesses, and matched skills for each candidate
- **No OpenAI Required**: Uses Google's Gemini API instead

## 📋 Requirements

1. **Python 3.8+**
2. **Google Gemini API Key** (Get it from [Google AI Studio](https://makersuite.google.com/app/apikey))

## 🔧 Setup Instructions

### Step 1: Install Dependencies

```bash
# Navigate to the project directory
cd c:\Users\RAVINDU\Desktop\OpenSource\Evalyn-backend

# Install required packages
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

1. Open the `.env` file in your project root
2. Add your **Gemini API Key**:

```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

3. Verify the threshold is set to 75%:

```bash
MINIMUM_MATCH_SCORE=75.0  # Candidates with 75% or above are automatically selected
```

### Step 3: Run the Application

```bash
# Start the backend server
python app/main.py

# Or using uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at: `http://localhost:8000`

## 📝 How It Works

### 1. Candidate Submits Application

Candidates apply through your career page at:
```
POST /api/v1/applications/apply
```

**Required fields:**
- Job ID
- Full Name
- Email
- CV File (PDF, DOCX, or DOC)
- Optional: Phone, LinkedIn, Portfolio, Cover Letter

### 2. AI Screening Process

HR can trigger screening for all pending applications:
```
POST /api/v1/applications/job/{job_id}/screen
```

**What happens:**
1. Gemini AI extracts text from each CV
2. Analyzes CV against job description and requirements
3. Scores each candidate (0-100%)
4. Identifies:
   - Match score
   - Summary of candidate profile
   - Strengths (matching qualifications)
   - Weaknesses/gaps
   - List of matched skills

### 3. Automatic Selection (75% Threshold)

**Selection Logic:**
- **≥75%**: Candidate is SHORTLISTED ✅
- **<75%**: Candidate is not selected ❌

Example output:
```
✓ John Doe: 85% - SELECTED (≥75%)
✓ Jane Smith: 78% - SELECTED (≥75%)
✗ Bob Johnson: 68% - Not selected (<75%)
```

### 4. View Results

Get all applications for a job:
```
GET /api/v1/applications/job/{job_id}
```

Filter by status:
```
GET /api/v1/applications/job/{job_id}?status_filter=shortlisted
```

## 🎯 Scoring Criteria

Gemini AI evaluates candidates based on:

| Score Range | Meaning | Action |
|-------------|---------|--------|
| 90-100% | Exceptional match, exceeds all requirements | Shortlisted |
| 75-89% | Strong match, meets/exceeds most requirements | Shortlisted |
| 60-74% | Good match, meets basic requirements | Not selected |
| 40-59% | Partial match, significant gaps | Rejected |
| 0-39% | Poor match, lacks key requirements | Rejected |

## 📊 API Endpoints

### Public Endpoints (Career Page)

#### Submit Application
```http
POST /api/v1/applications/apply
Content-Type: multipart/form-data

job_id: 1
full_name: John Doe
email: john@example.com
phone: +1234567890
cv_file: [file]
```

### HR Dashboard Endpoints

#### Screen Applications
```http
POST /api/v1/applications/job/1/screen
```

Response:
```json
{
  "job_id": 1,
  "total_applications": 20,
  "screened_count": 20,
  "shortlisted_candidates": [
    {
      "application_id": 5,
      "candidate_name": "John Doe",
      "email": "john@example.com",
      "ai_score": 85.0,
      "ai_summary": "Experienced software engineer with strong background in Python and cloud technologies...",
      "ai_strengths": "• 5+ years Python experience\n• AWS certified\n• Strong backend development",
      "ai_weaknesses": "• Limited frontend experience\n• No mobile development background",
      "skills_matched": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker"],
      "is_shortlisted": true
    }
  ],
  "message": "Screened 20 applications. Top 10 shortlisted."
}
```

#### Get Job Applications
```http
GET /api/v1/applications/job/1
```

#### Get Application Details
```http
GET /api/v1/applications/5
```

#### Get Statistics
```http
GET /api/v1/applications/job/1/statistics
```

## 🔐 Environment Variables

Complete `.env` configuration:

```bash
# Application Settings
APP_NAME="Evalyn HR Automation Agent"
DEBUG=true

# Database
DATABASE_URL=sqlite:///./evalyn_hr.db

# Google Gemini API Key (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=hr@yourcompany.com

# Company Information
COMPANY_NAME=Your Company Name
CAREERS_PAGE_URL=https://yourcompany.com/careers

# AI Agent Settings
CV_SCREENING_TOP_CANDIDATES=10
MINIMUM_MATCH_SCORE=75.0  # Candidates with 75% or above are automatically selected
```

## 🧪 Testing the System

### 1. Create a Test Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "department": "Engineering",
    "location": "Remote",
    "job_type": "Full-time",
    "experience_level": "Senior",
    "min_experience_years": 3,
    "max_experience_years": 7,
    "description": "We are looking for an experienced Python developer...",
    "requirements": "- 5+ years Python experience\n- FastAPI/Django expertise\n- AWS knowledge\n- PostgreSQL",
    "is_published": true
  }'
```

### 2. Submit Test Applications

Upload CVs through the API or use the Swagger UI at `http://localhost:8000/docs`

### 3. Run AI Screening

```bash
curl -X POST "http://localhost:8000/api/v1/applications/job/1/screen"
```

### 4. View Results

```bash
curl "http://localhost:8000/api/v1/applications/job/1?status_filter=shortlisted"
```

## 📈 Understanding the Results

Each candidate receives:

1. **Match Score** (0-100%): Overall fit for the position
2. **Summary**: Brief overview of candidate's profile
3. **Strengths**: What makes them a good fit
4. **Weaknesses**: Areas of concern or missing skills
5. **Skills Matched**: Specific skills from job requirements they possess
6. **Status**: 
   - `pending` - Just applied
   - `screening` - Being analyzed
   - `shortlisted` - Score ≥75%, selected for next round ✅
   - `rejected` - Did not meet threshold

## 🔄 Workflow

```
1. HR creates job posting → published to careers page
2. Candidates apply with CVs → stored in database
3. HR triggers AI screening → Gemini analyzes all CVs
4. System calculates match percentages → scores 0-100%
5. Candidates ≥75% automatically shortlisted → ready for interviews
6. HR reviews shortlisted candidates → detailed insights available
7. Send interview invitations → automated emails to selected candidates
```

## 🚨 Important Notes

- **75% Threshold**: Only candidates scoring 75% or above are shortlisted
- **Top N Selection**: By default, only top 10 candidates are considered (configurable)
- **Fair Evaluation**: Gemini provides objective analysis based on CV content vs job requirements
- **Manual Override**: HR can manually adjust candidate status if needed

## 🆘 Troubleshooting

### Gemini API Errors

If you get API errors:
1. Verify your API key is correct in `.env`
2. Check if you have quota remaining: https://makersuite.google.com/app/apikey
3. Ensure `google-generativeai` package is installed: `pip install google-generativeai`

### CV Extraction Issues

If CVs are not being read:
1. Ensure `pdfplumber` and `python-docx` are installed
2. Check file permissions in `uploads/cvs/` directory
3. Verify CV files are valid PDF or DOCX format

### Low Scores

If all candidates get low scores:
1. Review job description and requirements - make them clear and specific
2. Ensure CVs have relevant content
3. Check if CVs are in a readable format (not scanned images)

## 📚 Additional Resources

- **Gemini API Documentation**: https://ai.google.dev/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Get Gemini API Key**: https://makersuite.google.com/app/apikey

## 🎓 Pro Tips

1. **Clear Job Descriptions**: The more specific your job requirements, the better the matching
2. **Structured CVs**: Candidates with well-structured CVs get better analysis
3. **Regular Screening**: Run screening after collecting several applications for better comparison
4. **Review Insights**: Check the AI's strengths/weaknesses analysis to understand scoring
5. **Adjust Threshold**: If 75% is too high/low, adjust `MINIMUM_MATCH_SCORE` in `.env`

---

**Need Help?** Check the API documentation at `http://localhost:8000/docs` for interactive testing!
