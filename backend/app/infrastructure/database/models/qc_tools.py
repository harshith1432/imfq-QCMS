from datetime import datetime
from datetime import timezone, timezone
import json
import os
from sqlalchemy.dialects.postgresql import ARRAY
from app import db, bcrypt
from .base import SafeVector, Vector, is_local, _utc_now

class QCCheckSheet(db.Model):
    __tablename__ = 'qc_check_sheets'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    rows = db.relationship('QCCheckSheetRow', backref='check_sheet', cascade='all, delete-orphan')

class QCCheckSheetRow(db.Model):
    __tablename__ = 'qc_check_sheet_rows'
    id = db.Column(db.Integer, primary_key=True)
    check_sheet_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheets.id'), nullable=False)
    category_name = db.Column(db.String(255), nullable=False)
    total_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

class QCCheckSheetEntry(db.Model):
    __tablename__ = 'qc_check_sheet_entries'
    id = db.Column(db.Integer, primary_key=True)
    check_sheet_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheets.id'), nullable=False)
    row_id = db.Column(db.Integer, db.ForeignKey('qc_check_sheet_rows.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, default=1)
    inspector = db.Column(db.String(255))
    remarks = db.Column(db.Text)

class QCParetoChart(db.Model):
    __tablename__ = 'qc_pareto_charts'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 2, 5, or 6
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    total_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    items = db.relationship('QCParetoItem', backref='pareto_chart', cascade='all, delete-orphan')

class QCParetoItem(db.Model):
    __tablename__ = 'qc_pareto_items'
    id = db.Column(db.Integer, primary_key=True)
    pareto_chart_id = db.Column(db.Integer, db.ForeignKey('qc_pareto_charts.id'), nullable=False)
    cause_name = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    cumulative_pct = db.Column(db.Float)
    priority_rank = db.Column(db.Integer)

class QCStratification(db.Model):
    __tablename__ = 'qc_stratifications'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category_type = db.Column(db.String(100))  # Shift, Machine, Operator, Material
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    items = db.relationship('QCStratificationItem', backref='stratification', cascade='all, delete-orphan')

class QCStratificationItem(db.Model):
    __tablename__ = 'qc_stratification_items'
    id = db.Column(db.Integer, primary_key=True)
    stratification_id = db.Column(db.Integer, db.ForeignKey('qc_stratifications.id'), nullable=False)
    factor_name = db.Column(db.String(255), nullable=False)
    defect_count = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float)

class QCProcessMap(db.Model):
    __tablename__ = 'qc_process_maps'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=2)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    steps = db.relationship('QCProcessStep', backref='process_map', cascade='all, delete-orphan')

class QCProcessStep(db.Model):
    __tablename__ = 'qc_process_steps'
    id = db.Column(db.Integer, primary_key=True)
    process_map_id = db.Column(db.Integer, db.ForeignKey('qc_process_maps.id'), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50))  # Input, Process, Decision, Output
    description = db.Column(db.Text)
    next_step_id = db.Column(db.Integer)

class QCFishboneDiagram(db.Model):
    __tablename__ = 'qc_fishbone_diagrams'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer, default=4)
    effect = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    branches = db.relationship('QCFishboneBranch', backref='fishbone', cascade='all, delete-orphan')

class QCFishboneBranch(db.Model):
    __tablename__ = 'qc_fishbone_branches'
    id = db.Column(db.Integer, primary_key=True)
    fishbone_id = db.Column(db.Integer, db.ForeignKey('qc_fishbone_diagrams.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Man, Machine, Material, Method, Measurement, Environment
    parent_cause_id = db.Column(db.Integer, db.ForeignKey('qc_fishbone_branches.id'))
    text = db.Column(db.Text, nullable=False)

class QCScatterDiagram(db.Model):
    __tablename__ = 'qc_scatter_diagrams'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 4 or 5
    x_axis_label = db.Column(db.String(100))
    y_axis_label = db.Column(db.String(100))
    correlation_coefficient = db.Column(db.Float)
    correlation_type = db.Column(db.String(50))  # Positive, Negative, None
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    points = db.relationship('QCScatterPoint', backref='scatter', cascade='all, delete-orphan')

class QCScatterPoint(db.Model):
    __tablename__ = 'qc_scatter_points'
    id = db.Column(db.Integer, primary_key=True)
    scatter_diagram_id = db.Column(db.Integer, db.ForeignKey('qc_scatter_diagrams.id'), nullable=False)
    x_value = db.Column(db.Float, nullable=False)
    y_value = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text)

class QCControlChart(db.Model):
    __tablename__ = 'qc_control_charts'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    stage_id = db.Column(db.Integer)  # Can be 4 or 6
    title = db.Column(db.String(255), nullable=False)
    chart_type = db.Column(db.String(50), default='Xbar-R')
    mean = db.Column(db.Float)
    ucl = db.Column(db.Float)
    lcl = db.Column(db.Float)
    std_dev = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=_utc_now)
    
    points = db.relationship('QCControlPoint', backref='control_chart', cascade='all, delete-orphan')

class QCControlPoint(db.Model):
    __tablename__ = 'qc_control_points'
    id = db.Column(db.Integer, primary_key=True)
    control_chart_id = db.Column(db.Integer, db.ForeignKey('qc_control_charts.id'), nullable=False)
    sample_index = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Float, nullable=False)
    is_out_of_control = db.Column(db.Boolean, default=False)


