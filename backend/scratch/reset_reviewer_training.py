import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.infrastructure.database.models.models import db, SOPTraining, SOPAcknowledgement, SOPAssessmentResult

app = create_app()

with app.app_context():
    # 1. Reset training assignment 33
    t = SOPTraining.query.get(33)
    if t:
        t.status = 'Not Started'
        t.read_status = False
        t.acknowledgement_status = False
        t.training_completion_status = False
        t.assessment_score = None
        t.completed_at = None
        t.attempts_left = 3
        t.total_reading_time = 0
        t.reading_percentage = 0.0
        print("Reset training assignment 33")
        
    # 2. Delete acknowledgements
    SOPAcknowledgement.query.filter_by(training_id=33).delete()
    print("Deleted acknowledgements for training 33")
    
    # 3. Delete assessment results
    SOPAssessmentResult.query.filter_by(training_id=33).delete()
    print("Deleted assessment results for training 33")
    
    db.session.commit()
    print("Database committed successfully.")
