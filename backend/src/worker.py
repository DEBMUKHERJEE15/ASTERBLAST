import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .database import SessionLocal
from . import crud, schemas
from .config import settings

logger = logging.getLogger(__name__)

class AlertWorker:
    def __init__(self):
        self.running = False
        
    async def start(self):
        """Start the alert worker"""
        self.running = True
        logger.info("Alert worker started")
        
        while self.running:
            try:
                await self.check_upcoming_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Alert worker error: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the alert worker"""
        self.running = False
        logger.info("Alert worker stopped")
    
    async def check_upcoming_alerts(self):
        """Check for upcoming close approaches and send alerts"""
        db = SessionLocal()
        try:
            # Get all active alerts
            alerts = []
            # This would fetch from database in production
            
            # Check next 24 hours
            check_date = datetime.now() + timedelta(days=1)
            
            # Fetch upcoming asteroids from NASA
            from .neo_fetcher import get_nasa_fetcher
            fetcher = await get_nasa_fetcher()
            
            data = await fetcher.fetch_feed(
                datetime.now().strftime("%Y-%m-%d"),
                check_date.strftime("%Y-%m-%d")
            )
            
            upcoming_asteroids = data.get("asteroids", [])
            
            # Check each alert against upcoming asteroids
            for alert in alerts:
                for asteroid in upcoming_asteroids:
                    if asteroid["id"] == alert.asteroid_id:
                        # Check if criteria are met
                        distance_km = asteroid.get("miss_distance_km", float('inf'))
                        risk_score = asteroid.get("risk_score", 0)
                        
                        if (distance_km <= alert.threshold_distance_km or
                            risk_score >= alert.threshold_risk_score):
                            
                            # Trigger alert
                            await self.send_alert_notification(alert, asteroid)
                            
                            # Update alert in database
                            crud.AlertCRUD.update_alert_triggered(db, alert.id)
            
            logger.info(f"Checked {len(upcoming_asteroids)} upcoming asteroids")
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
        finally:
            db.close()
    
    async def send_alert_notification(self, alert, asteroid):
        """Send alert notification to user"""
        try:
            # Get user details
            db = SessionLocal()
            user = crud.UserCRUD.get_user(db, alert.user_id)
            db.close()
            
            if not user:
                return
            
            # Prepare notification message
            subject = f"🚨 COSMIC WATCH ALERT: {asteroid.get('name')}"
            
            message = f"""
            ⚠️ ASTEROID ALERT TRIGGERED ⚠️
            
            Alert: {alert.name}
            Asteroid: {asteroid.get('name')}
            Close Approach: {asteroid.get('close_approach_date')}
            
            Details:
            - Estimated Diameter: {asteroid.get('estimated_diameter_km', 'N/A')} km
            - Miss Distance: {asteroid.get('miss_distance_km', 'N/A'):,.0f} km
            - Relative Velocity: {asteroid.get('relative_velocity_kph', 'N/A'):,.0f} km/h
            - Risk Score: {asteroid.get('risk_score', 'N/A')}/100
            - Threat Level: {asteroid.get('threat_level', 'N/A')}
            
            Your alert was triggered because:
            • Miss distance threshold: {alert.threshold_distance_km} km
            • Risk score threshold: {alert.threshold_risk_score}/100
            
            Stay informed at: http://localhost:3000/alerts
            
            ---
            Cosmic Watch Monitoring System
            """
            
            # Send notification based on user preference
            if alert.notification_method == "email":
                await self.send_email(user.email, subject, message)
            elif alert.notification_method == "dashboard":
                # Store notification in database for dashboard
                db = SessionLocal()
                crud.NotificationCRUD.create_notification(
                    db, 
                    user.id,
                    subject,
                    message,
                    "alert"
                )
                db.close()
            
            logger.info(f"Alert sent for asteroid {asteroid.get('name')} to user {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    async def send_email(self, to_email: str, subject: str, body: str):
        """Send email notification"""
        if not all([settings.SMTP_HOST, settings.SMTP_PORT, 
                   settings.SMTP_USER, settings.SMTP_PASSWORD]):
            logger.warning("Email configuration missing, skipping email send")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

# Global worker instance
alert_worker = AlertWorker()

async def start_alert_worker():
    """Start the alert worker"""
    await alert_worker.start()

async def stop_alert_worker():
    """Stop the alert worker"""
    await alert_worker.stop()