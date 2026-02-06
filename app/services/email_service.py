"""
Email Service for sending notifications to candidates
Handles: Shortlist notifications, Interview invitations, etc.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job


class EmailService:
    """Service for sending HR-related emails"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.company_name = settings.COMPANY_NAME
    
    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email using SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.company_name} HR <{self.email_from}>"
            msg["To"] = to_email
            
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, to_email, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def send_shortlist_notification(
        self, 
        application: Application, 
        job: Job
    ) -> bool:
        """
        Send email to candidate who passed Round 1 (AI Screening)
        Notifying them they're shortlisted for Round 2 interview
        """
        subject = f"Congratulations! You've been shortlisted for {job.title} at {self.company_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4A90A4; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .highlight {{ background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Congratulations!</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{application.full_name}</strong>,</p>
                    
                    <p>We are pleased to inform you that you have successfully passed the 
                    <strong>first round of screening</strong> for the position of 
                    <strong>{job.title}</strong> at {self.company_name}.</p>
                    
                    <div class="highlight">
                        <h3>✅ Round 1: Passed</h3>
                        <p>Your qualifications and experience have impressed our team!</p>
                    </div>
                    
                    <h3>Next Steps: Round 2 Interview</h3>
                    <p>You have been selected to proceed to the <strong>second round</strong>, 
                    which will be a technical interview with our Senior Software Engineer (SSE).</p>
                    
                    <p>You will receive a separate email shortly with the interview schedule 
                    and meeting details.</p>
                    
                    <p>Please make sure to:</p>
                    <ul>
                        <li>Review the job description and requirements</li>
                        <li>Prepare to discuss your relevant experience</li>
                        <li>Have questions ready about the role and team</li>
                    </ul>
                    
                    <p>If you have any questions, please don't hesitate to reach out.</p>
                    
                    <p>Best regards,<br>
                    <strong>HR Team</strong><br>
                    {self.company_name}</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {self.company_name} Recruitment System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(application.email, subject, html_body)
    
    def send_interview_invitation(
        self, 
        application: Application, 
        interview: Interview,
        job: Job
    ) -> bool:
        """Send interview schedule/invitation email"""
        scheduled_time = interview.scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p")
        
        subject = f"Interview Scheduled: {job.title} - Round 2 at {self.company_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .schedule-box {{ background: #fff; border: 2px solid #2196F3; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .btn {{ display: inline-block; background: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Interview Scheduled</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{application.full_name}</strong>,</p>
                    
                    <p>Your Round 2 interview for <strong>{job.title}</strong> has been scheduled.</p>
                    
                    <div class="schedule-box">
                        <h3>📋 Interview Details</h3>
                        <p><strong>Position:</strong> {job.title}</p>
                        <p><strong>Round:</strong> {interview.round.replace('round', 'Round ').title()}</p>
                        <p><strong>Date & Time:</strong> {scheduled_time}</p>
                        <p><strong>Duration:</strong> {interview.duration_minutes} minutes</p>
                        <p><strong>Interviewer:</strong> {interview.interviewer_name}</p>
                        {"<p><strong>Location:</strong> " + interview.location + "</p>" if interview.location else ""}
                        {"<p><strong>Meeting Link:</strong> <a href='" + interview.meeting_link + "'>" + interview.meeting_link + "</a></p>" if interview.meeting_link else ""}
                    </div>
                    
                    <h3>📝 Preparation Tips</h3>
                    <ul>
                        <li>Join the meeting 5 minutes early</li>
                        <li>Ensure your camera and microphone are working</li>
                        <li>Have a copy of your CV ready</li>
                        <li>Prepare examples of your past work</li>
                    </ul>
                    
                    {f'<a href="{interview.meeting_link}" class="btn">Join Interview Meeting</a>' if interview.meeting_link else ''}
                    
                    <p>If you need to reschedule, please reply to this email at least 24 hours before the scheduled time.</p>
                    
                    <p>Best of luck!</p>
                    
                    <p>Best regards,<br>
                    <strong>HR Team</strong><br>
                    {self.company_name}</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {self.company_name} Recruitment System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(application.email, subject, html_body)
    
    def send_rejection_email(
        self,
        application: Application,
        job: Job
    ) -> bool:
        """Send polite rejection email"""
        subject = f"Application Update: {job.title} at {self.company_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #607D8B; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Update</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{application.full_name}</strong>,</p>
                    
                    <p>Thank you for your interest in the <strong>{job.title}</strong> position 
                    at {self.company_name} and for taking the time to apply.</p>
                    
                    <p>After careful review of all applications, we regret to inform you that 
                    we have decided to move forward with other candidates whose qualifications 
                    more closely match our current needs.</p>
                    
                    <p>We truly appreciate your interest in joining our team and encourage you 
                    to apply for future openings that match your skills and experience.</p>
                    
                    <p>We wish you all the best in your job search and future career endeavors.</p>
                    
                    <p>Best regards,<br>
                    <strong>HR Team</strong><br>
                    {self.company_name}</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {self.company_name} Recruitment System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(application.email, subject, html_body)
    
    def send_bulk_shortlist_notifications(
        self,
        applications: List[Application],
        job: Job
    ) -> dict:
        """Send shortlist emails to multiple candidates"""
        results = {"success": 0, "failed": 0, "emails": []}
        
        for app in applications:
            success = self.send_shortlist_notification(app, job)
            if success:
                results["success"] += 1
                results["emails"].append({"email": app.email, "status": "sent"})
            else:
                results["failed"] += 1
                results["emails"].append({"email": app.email, "status": "failed"})
        
        return results


# Singleton instance
email_service = EmailService()
