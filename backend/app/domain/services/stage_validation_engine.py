"""
QCMS Stage Completion Validation Engine & Workflow State Machine
Enforces strict sequential progression (S1 -> S2 -> ... -> S8),
validates mandatory fields and artifacts per stage, and prevents illegal transitions.
"""

from typing import Tuple, List, Dict, Any, Optional
from app import db
from app.infrastructure.database.models.workflow import (
    Stage1ProblemDefinitionProjectInitiation,
    Stage2ObservationDataCollection,
    Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification,
    Stage5CountermeasurePlanningSolutionDevelopment,
    Stage6ImplementationChangeManagement,
    Stage7PerformanceVerificationBenefitsRealization,
    Stage8StandardizationKnowledgeSharingProjectClosure
)


class StageValidationEngine:
    """Validates completeness and readiness of QCMS workflow stages."""

    STAGE_MODELS = {
        1: Stage1ProblemDefinitionProjectInitiation,
        2: Stage2ObservationDataCollection,
        3: Stage3CauseIdentification,
        4: Stage4RootCauseAnalysisVerification,
        5: Stage5CountermeasurePlanningSolutionDevelopment,
        6: Stage6ImplementationChangeManagement,
        7: Stage7PerformanceVerificationBenefitsRealization,
        8: Stage8StandardizationKnowledgeSharingProjectClosure
    }

    STAGE_NAMES = {
        1: "Stage 1: Problem Definition & Initiation",
        2: "Stage 2: Observation & Data Collection",
        3: "Stage 3: Cause Identification",
        4: "Stage 4: Root Cause Analysis & Verification",
        5: "Stage 5: Countermeasure Planning & Solution Development",
        6: "Stage 6: Implementation & Change Management",
        7: "Stage 7: Performance Verification & Benefits Realization",
        8: "Stage 8: Standardization & Project Closure"
    }

    @classmethod
    def validate_stage(cls, project_id: int, stage_number: int) -> Tuple[bool, List[str]]:
        """Validate if a stage has met all required completion criteria to advance.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        model_cls = cls.STAGE_MODELS.get(stage_number)
        if not model_cls:
            return False, [f"Invalid stage number: {stage_number}"]

        stage_record = model_cls.query.filter_by(project_id=project_id).first()
        if not stage_record:
            return False, [f"No stage details recorded for {cls.STAGE_NAMES.get(stage_number, f'Stage {stage_number}')}. Please save the stage work before advancing."]

        validator_method = getattr(cls, f"_validate_stage_{stage_number}", None)
        if validator_method:
            stage_errors = validator_method(stage_record)
            errors.extend(stage_errors)

        return len(errors) == 0, errors

    @staticmethod
    def _is_empty(val: Any) -> bool:
        if val is None:
            return True
        if isinstance(val, (str, list, dict)) and len(val) == 0:
            return True
        return False

    @classmethod
    def _validate_stage_1(cls, record: Stage1ProblemDefinitionProjectInitiation) -> List[str]:
        errs = []
        if cls._is_empty(record.problem_5w2h) and cls._is_empty(record.project_team):
            errs.append("Stage 1 requires problem definition (5W2H) or project team assignments.")
        return errs

    @classmethod
    def _validate_stage_2(cls, record: Stage2ObservationDataCollection) -> List[str]:
        errs = []
        if cls._is_empty(record.data_collection_plan) and cls._is_empty(record.gemba_observations):
            errs.append("Stage 2 requires a data collection plan or Gemba observation log.")
        return errs

    @classmethod
    def _validate_stage_3(cls, record: Stage3CauseIdentification) -> List[str]:
        errs = []
        if cls._is_empty(record.brainstorming_ideas) and cls._is_empty(record.cause_and_effect):
            errs.append("Stage 3 requires brainstorming ideas or cause-and-effect (Ishikawa) analysis.")
        return errs

    @classmethod
    def _validate_stage_4(cls, record: Stage4RootCauseAnalysisVerification) -> List[str]:
        errs = []
        if cls._is_empty(record.five_why_analysis) and cls._is_empty(record.root_cause_verification):
            errs.append("Stage 4 requires 5-Why analysis or root cause verification evidence.")
        return errs

    @classmethod
    def _validate_stage_5(cls, record: Stage5CountermeasurePlanningSolutionDevelopment) -> List[str]:
        errs = []
        if cls._is_empty(record.proposed_countermeasures) and cls._is_empty(record.action_plan_5w1h):
            errs.append("Stage 5 requires proposed countermeasures or a 5W1H action plan.")
        return errs

    @classmethod
    def _validate_stage_6(cls, record: Stage6ImplementationChangeManagement) -> List[str]:
        errs = []
        if cls._is_empty(record.pilot_execution) and cls._is_empty(record.full_scale_implementation):
            errs.append("Stage 6 requires pilot execution logs or implementation milestones.")
        return errs

    @classmethod
    def _validate_stage_7(cls, record: Stage7PerformanceVerificationBenefitsRealization) -> List[str]:
        errs = []
        if cls._is_empty(record.before_after_comparison) and cls._is_empty(record.tangible_benefits):
            errs.append("Stage 7 requires before/after performance comparison or tangible benefits calculation.")
        return errs

    @classmethod
    def _validate_stage_8(cls, record: Stage8StandardizationKnowledgeSharingProjectClosure) -> List[str]:
        errs = []
        if cls._is_empty(record.sop_standardization) and cls._is_empty(record.lessons_learned):
            errs.append("Stage 8 requires SOP standardization updates or lessons learned documentation.")
        return errs

    @classmethod
    def validate_transition(cls, project, target_stage: int) -> Tuple[bool, Optional[str], int]:
        """Validate state machine rules and sequential stage transition constraints.
        
        Returns:
            (is_allowed, error_message, http_status_code)
        """
        current_stage = project.current_stage or 1

        # Check project state
        if project.status in ('Cancelled', 'Closed', 'Archived'):
            return False, f"Cannot advance stage: project is currently '{project.status}'.", 400

        # Boundary checks
        if target_stage < 1 or target_stage > 8:
            return False, f"Invalid stage {target_stage}. Valid stages are 1 through 8.", 400

        # Strict sequential transition enforcement (No stage skipping)
        if target_stage > current_stage + 1:
            return False, f"Stage skip blocked. You must advance sequentially from Stage {current_stage} to Stage {current_stage + 1}.", 400

        # Disallow moving backwards through transitions endpoint
        if target_stage <= current_stage:
            return False, f"Project is already at Stage {current_stage}. Target stage must be {current_stage + 1}.", 400

        # Validate completion of the current stage before advancing
        is_valid, validation_errors = cls.validate_stage(project.id, current_stage)
        if not is_valid:
            error_details = " | ".join(validation_errors)
            return False, f"Stage {current_stage} completion requirements not met: {error_details}", 422

        return True, None, 200
