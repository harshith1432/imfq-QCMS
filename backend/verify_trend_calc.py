import sys
with open("trend_calc_out.txt", "w") as out_f:
    try:
        from app import create_app, db
        from app.infrastructure.database.models.models import User, Project
        from sqlalchemy import func
        from datetime import datetime, timedelta

        app = create_app()
        with app.app_context():
            org_id = 3
            trend_from = datetime.utcnow() - timedelta(days=180)
            
            completed_monthly_q = db.session.query(
                func.to_char(Project.created_at, 'YYYY-MM').label('month'),
                func.count(Project.id).label('count')
            ).filter(
                Project.org_id == org_id,
                Project.status.in_(['Closed', 'Completed', 'Archived']),
                Project.created_at >= trend_from
            )
            comp_month_map = {r.month: r.count for r in completed_monthly_q.group_by('month').all() if r.month}

            active_monthly_q = db.session.query(
                func.to_char(Project.created_at, 'YYYY-MM').label('month'),
                func.count(Project.id).label('count')
            ).filter(
                Project.org_id == org_id,
                ~Project.status.in_(['Closed', 'Completed', 'Archived']),
                Project.created_at >= trend_from
            )
            act_month_map = {r.month: r.count for r in active_monthly_q.group_by('month').all() if r.month}

            all_trend_months = sorted(list(set(comp_month_map.keys()) | set(act_month_map.keys())))
            if not all_trend_months:
                all_trend_months = [datetime.utcnow().strftime('%Y-%m')]

            out_f.write("=========================================\n")
            out_f.write(f"Org ID: {org_id} ('youtube')\n")
            for m_key in all_trend_months:
                month_label = datetime.strptime(m_key, '%Y-%m').strftime('%b %Y')
                c_cnt = comp_month_map.get(m_key, 0)
                a_cnt = act_month_map.get(m_key, 0)
                out_f.write(f"Month: {month_label} => Projects Completed: {c_cnt}, Active Initiatives: {a_cnt}, Total: {c_cnt + a_cnt}\n")
            out_f.write("=========================================\n")
    except Exception as e:
        out_f.write(str(e))
