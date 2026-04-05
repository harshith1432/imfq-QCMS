import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app, db
from backend.app.models import User, Department

app = create_app()

with app.app_context():
    # Find team leader
    tl = User.query.filter_by(email='teamleader1@gmail.com').first()
    if not tl:
        print("Team leader (teamleader1@gmail.com) not found.")
        sys.exit(1)
    
    print(f"Current Team Leader: {tl.username}, DeptID: {tl.department_id}")
    if tl.dept:
        print(f"Current Dept: {tl.dept.name}")
    else:
        print("Current Dept: N/A")
    
    # Check if 'Quality Control' exists for this org
    qc_dept = Department.query.filter_by(name='Quality Control', org_id=tl.org_id).first()
    if qc_dept:
        print(f"Quality Control dept exists: ID {qc_dept.id}")
    else:
        print("Quality Control dept does not exist for this org.")

    # We won't perform the update here, just verifying the logic state.
    # The fix in admin_routes.py will now handle the missing dept or org mismatch.
