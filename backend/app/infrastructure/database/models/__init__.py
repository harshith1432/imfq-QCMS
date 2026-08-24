# Re-export all database models across specialized submodules for 100% backward compatibility
from app import db, bcrypt
from .base import SafeVector, Vector, is_local
from .tenant import Organization, Plant, Department, OrgApiKey, OrganizationFeatureOverride
from .auth import Role, User, SaaSUserSession, EmailVerification, PhoneVerification, UserCustomField
from .workflow import (
    Project, ProjectMember, ProjectStageTracker, ProjectWorkflow, ProjectMeeting,
    Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, Stage6ImplementationChangeManagement,
    Stage7PerformanceVerificationBenefitsRealization, Stage8StandardizationKnowledgeSharingProjectClosure,
    ProjectReview, KPIMetric, FacilitatorNote, FacilitatorAssistanceRequest, EmployeePoints, EmployeeLeaderboard, ImportedIdea
)
from .qc_tools import (
    QCCheckSheet, QCCheckSheetRow, QCCheckSheetEntry,
    QCParetoChart, QCParetoItem, QCStratification, QCStratificationItem,
    QCProcessMap, QCProcessStep, QCFishboneDiagram, QCFishboneBranch,
    QCScatterDiagram, QCScatterPoint, QCControlChart, QCControlPoint
)
from .audit import (
    AuditLog, AuditRiskAlert, AuditExportLog, KnowledgeRepository, KPIDashboardCache,
    SuperAdminLog, SOPCategory, SOPType, SOP, SOPStep, SOPApproval, SOPVersion,
    SOPTraining, SOPComment, Notification, SOPAcknowledgement, SOPAssessment,
    SOPAssessmentQuestion, SOPAssessmentResult, SOPAuditReport,
    SOPArchive, SOPNotification, ComplianceStandard
)
from .billing import (
    PlatformSettings, SupportTicket, SupportComment, SupportAttachment, SupportSLA,
    SupportEscalation, SupportRating, SupportKnowledge, SupportAudit, SalesEnquiry,
    SubscriptionPayment, Subscription, OfflinePaymentProof, SubscriptionInvoice,
    SaaSPlan, SaaSPlanPricing, SaaSPlanLimits, SaaSPlanModules, SaaSPlanVersion, SaaSPlanAnalytics,
    Module, FeatureCategory, FeatureVersion, ModuleDependency, ModuleAssignment, ModulePermission,
    ModuleUsageAnalytics, ModuleAuditLog, AnalyticsCache, AnalyticsReport, AnalyticsSchedule,
    AnalyticsExport, AnalyticsAIInsights, AnalyticsUsage, InvoiceItem, SubscriptionRefund,
    SubscriptionCreditNote, BillingSettings, TaxRule, BillingAudit, Announcement,
    AnnouncementAudience, AnnouncementDelivery, AnnouncementRead, AnnouncementAttachment,
    AnnouncementAudit, IntegrationConfig, IntegrationApiKey, IntegrationWebhook,
    IntegrationWebhookDelivery, IntegrationAuditLog, IntegrationApiLog,
    PlatformIdentityConfig, CompanyInformationConfig, CompanyContactsConfig,
    CompanyAddressesConfig, BrandingAssetsConfig, DocumentTemplateConfig, SettingUsageMap,
    EmailNotificationRule, SmsTemplateConfig, EmailNotificationLog, SmsNotificationLog,
    SubscriptionPlan, BillingInvoice
)
from .audit import SOPMaster
from .workflow import (
    Stage1, Stage2, Stage3, Stage4, Stage5, Stage6, Stage7, Stage8,
    Stage1ProblemDefinition, Stage2Observation, Stage3Cause, Stage4RootCause,
    Stage5Countermeasure, Stage6Implementation, Stage7Performance, Stage8Standardization,
    Stage8Implementation, Stage1Identification, Stage2Selection, Stage3Analysis,
    Stage4Causes, Stage5RootCause, Stage6DataAnalysis, Stage7Development,
    Stage1Problem, Stage3RCA, Stage4Solution, Stage5Approval, Stage7Impact
)


