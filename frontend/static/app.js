const DEFAULT_DASHBOARD_WORKSPACE_ID = "safe_access_kfar_saba_route_aware_v001";
const DEFAULT_TRANSIT_PROFILE_WORKSPACE_ID = "transit_stop_walk_access_kfar_saba_v001";
const DEFAULT_PARK_PROFILE_WORKSPACE_ID = "park_playground_access_kfar_saba_v001";
const DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID = "osm_tag_quality_kfar_saba_v001";
const DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID = "authored_profile_audit_kfar_saba_v001";

const state = {
  summary: null,
  features: null,
  candidates: [],
  decisions: {},
  decisionSummary: null,
  mapView: null,
  sources: [],
  sourceOnboarding: null,
  localIntake: null,
  localIntakePreview: null,
  localIntakePlan: null,
  sourceImportGuardrails: null,
  sourceImportPreview: null,
  sourceImportRequest: null,
  sourceImportDecision: null,
  sourceHandoff: null,
  sourceHandoffCreated: null,
  sourceHandoffExecution: null,
  sourceHandoffExecutionCreated: null,
  executionEvidencePackage: null,
  executionEvidencePackageCreated: null,
  executionResultDiff: null,
  executionResultDiffCreated: null,
  executionDiffGallery: null,
  executionDiffGalleryCreated: null,
  executionDiffDetail: null,
  executionDiffDetailCreated: null,
  reproducibilityAuditPacket: null,
  reproducibilityAuditPacketCreated: null,
  reviewerAuditIndex: null,
  reviewerAuditIndexCreated: null,
  portfolioExportLauncher: null,
  portfolioExportLauncherCreated: null,
  portableReleasePackage: null,
  portableReleasePackageCreated: null,
  demoScriptPack: null,
  demoScriptPackCreated: null,
  visualQALedger: null,
  visualQALedgerCreated: null,
  visualBaselineComparison: null,
  visualBaselineComparisonCreated: null,
  demoArtifactCompleteness: null,
  demoArtifactCompletenessCreated: null,
  visualEvidenceCapture: null,
  visualEvidenceCaptureCreated: null,
  visualEvidenceReviewDiff: null,
  visualEvidenceReviewDiffCreated: null,
  visualEvidenceReviewAnnotations: null,
  visualEvidenceReviewAnnotationsCreated: null,
  visualEvidenceSignoffPacket: null,
  visualEvidenceSignoffPacketCreated: null,
  finalReviewerLaunchChecklist: null,
  finalReviewerLaunchChecklistCreated: null,
  recruiterDemoBrief: null,
  recruiterDemoBriefCreated: null,
  publicPortfolioPackage: null,
  publicPortfolioPackageCreated: null,
  demoReviewPlaybook: null,
  demoReviewPlaybookCreated: null,
  githubPublicationBundle: null,
  githubPublicationBundleCreated: null,
  repositoryPublicationQa: null,
  repositoryPublicationQaCreated: null,
  repositoryExportHandoff: null,
  repositoryExportHandoffCreated: null,
  repositoryDryRunReview: null,
  repositoryDryRunReviewCreated: null,
  repositoryFinalPackageReview: null,
  repositoryFinalPackageReviewCreated: null,
  publicReadmeCleanupReview: null,
  publicReadmeCleanupReviewCreated: null,
  publicRepositoryPolishPackage: null,
  publicRepositoryPolishPackageCreated: null,
  repositoryExportChecklist: null,
  repositoryExportChecklistCreated: null,
  analysisProfiles: null,
  profileWorkspaces: [],
  templates: [],
  workspaces: [],
  pilots: [],
  pilotMetadata: null,
  pilotPreflight: null,
  analysisPlan: null,
  analysisRuns: [],
  portfolioReports: [],
  exportBundles: [],
  productArchitecture: null,
  releaseReadiness: null,
  releaseReadinessSnapshot: null,
  portfolioDemo: null,
  portfolioDemoSnapshot: null,
  portfolioEvidenceBundle: null,
  portfolioEvidenceBundleCreated: null,
  bundleReviewChecklist: null,
  bundleReviewChecklistCreated: null,
  portfolioNarrative: null,
  portfolioNarrativeCreated: null,
  portfolioHandoff: null,
  portfolioHandoffCreated: null,
  portfolioEvidenceGallery: null,
  portfolioEvidenceGalleryCreated: null,
  multiPilotComparison: null,
  multiPilotComparisonCreated: null,
  comparisonMapExports: null,
  comparisonMapExportCreated: null,
  profileDashboard: null,
  profileDashboardSummary: null,
  profileDashboardResults: [],
  scoringRules: null,
  scoringAudit: null,
  postgisBackend: null,
  postgisPlan: null,
  profileMapper: null,
  profileMapperPlan: null,
  contractExecution: null,
  contractDryRun: null,
  osmTagQuality: null,
  osmTagQualityRun: null,
  templateAuthoring: null,
  templateDraft: null,
  authoredProfileRunner: null,
  authoredProfileRun: null,
  authoredQueueJob: null,
  profilePromotion: null,
  profilePromotionProposal: null,
  profileAcceptanceDecision: null,
  profileContractDiff: null,
  profileApplicationPlan: null,
  profileConfigApplyProposal: null,
  profileRegressionPreview: null,
  executionQueue: null,
  executionQueueJob: null,
  datasetPackages: null,
  datasetPackage: null,
  jobs: [],
  activeWorkspaceId: "",
  sourceProfile: null,
  templateCheck: null,
  selected: null,
};

const els = {
  status: document.getElementById("status"),
  overviewGeneratorCount: document.getElementById("overviewGeneratorCount"),
  overviewCrossingCount: document.getElementById("overviewCrossingCount"),
  overviewMajorRoadCount: document.getElementById("overviewMajorRoadCount"),
  overviewValidationStatus: document.getElementById("overviewValidationStatus"),
  showAdvancedControls: document.getElementById("showAdvancedControls"),
  controlPanel: document.getElementById("controlPanel"),
  buildSelectedPilotShortcut: document.getElementById("buildSelectedPilotShortcut"),
  dashboardWorkspaceSelect: document.getElementById("dashboardWorkspaceSelect"),
  sourceSelect: document.getElementById("sourceSelect"),
  templateSelect: document.getElementById("templateSelect"),
  refreshSourceOnboarding: document.getElementById("refreshSourceOnboarding"),
  sourceOnboardingStatus: document.getElementById("sourceOnboardingStatus"),
  sourceOnboardingBody: document.getElementById("sourceOnboardingBody"),
  localIntakePath: document.getElementById("localIntakePath"),
  previewLocalIntake: document.getElementById("previewLocalIntake"),
  createLocalIntakePlan: document.getElementById("createLocalIntakePlan"),
  localIntakeStatus: document.getElementById("localIntakeStatus"),
  localIntakeBody: document.getElementById("localIntakeBody"),
  refreshSourceImportGuardrails: document.getElementById("refreshSourceImportGuardrails"),
  previewSourceImportGuardrails: document.getElementById("previewSourceImportGuardrails"),
  createSourceImportReview: document.getElementById("createSourceImportReview"),
  approveSourceImportReview: document.getElementById("approveSourceImportReview"),
  sourceImportGuardrailsStatus: document.getElementById("sourceImportGuardrailsStatus"),
  sourceImportGuardrailsBody: document.getElementById("sourceImportGuardrailsBody"),
  refreshSourceHandoff: document.getElementById("refreshSourceHandoff"),
  createSourceHandoff: document.getElementById("createSourceHandoff"),
  sourceHandoffStatus: document.getElementById("sourceHandoffStatus"),
  sourceHandoffBody: document.getElementById("sourceHandoffBody"),
  refreshSourceHandoffExecution: document.getElementById("refreshSourceHandoffExecution"),
  executeSourceHandoff: document.getElementById("executeSourceHandoff"),
  sourceHandoffExecutionStatus: document.getElementById("sourceHandoffExecutionStatus"),
  sourceHandoffExecutionBody: document.getElementById("sourceHandoffExecutionBody"),
  refreshExecutionEvidencePackage: document.getElementById("refreshExecutionEvidencePackage"),
  createExecutionEvidencePackage: document.getElementById("createExecutionEvidencePackage"),
  executionEvidencePackageStatus: document.getElementById("executionEvidencePackageStatus"),
  executionEvidencePackageBody: document.getElementById("executionEvidencePackageBody"),
  refreshExecutionResultDiff: document.getElementById("refreshExecutionResultDiff"),
  createExecutionResultDiff: document.getElementById("createExecutionResultDiff"),
  executionResultDiffStatus: document.getElementById("executionResultDiffStatus"),
  executionResultDiffBody: document.getElementById("executionResultDiffBody"),
  refreshExecutionDiffGallery: document.getElementById("refreshExecutionDiffGallery"),
  createExecutionDiffGallery: document.getElementById("createExecutionDiffGallery"),
  executionDiffGalleryStatus: document.getElementById("executionDiffGalleryStatus"),
  executionDiffGalleryBody: document.getElementById("executionDiffGalleryBody"),
  refreshExecutionDiffDetail: document.getElementById("refreshExecutionDiffDetail"),
  createExecutionDiffDetail: document.getElementById("createExecutionDiffDetail"),
  executionDiffDetailStatus: document.getElementById("executionDiffDetailStatus"),
  executionDiffDetailBody: document.getElementById("executionDiffDetailBody"),
  refreshReproducibilityAuditPacket: document.getElementById("refreshReproducibilityAuditPacket"),
  createReproducibilityAuditPacket: document.getElementById("createReproducibilityAuditPacket"),
  reproducibilityAuditPacketStatus: document.getElementById("reproducibilityAuditPacketStatus"),
  reproducibilityAuditPacketBody: document.getElementById("reproducibilityAuditPacketBody"),
  refreshReviewerAuditIndex: document.getElementById("refreshReviewerAuditIndex"),
  createReviewerAuditIndex: document.getElementById("createReviewerAuditIndex"),
  reviewerAuditIndexStatus: document.getElementById("reviewerAuditIndexStatus"),
  reviewerAuditIndexBody: document.getElementById("reviewerAuditIndexBody"),
  refreshPortfolioExportLauncher: document.getElementById("refreshPortfolioExportLauncher"),
  createPortfolioExportLauncher: document.getElementById("createPortfolioExportLauncher"),
  portfolioExportLauncherStatus: document.getElementById("portfolioExportLauncherStatus"),
  portfolioExportLauncherBody: document.getElementById("portfolioExportLauncherBody"),
  refreshPortableReleasePackage: document.getElementById("refreshPortableReleasePackage"),
  createPortableReleasePackage: document.getElementById("createPortableReleasePackage"),
  portableReleasePackageStatus: document.getElementById("portableReleasePackageStatus"),
  portableReleasePackageBody: document.getElementById("portableReleasePackageBody"),
  refreshDemoScriptPack: document.getElementById("refreshDemoScriptPack"),
  createDemoScriptPack: document.getElementById("createDemoScriptPack"),
  demoScriptPackStatus: document.getElementById("demoScriptPackStatus"),
  demoScriptPackBody: document.getElementById("demoScriptPackBody"),
  refreshVisualQALedger: document.getElementById("refreshVisualQALedger"),
  createVisualQALedger: document.getElementById("createVisualQALedger"),
  visualQALedgerStatus: document.getElementById("visualQALedgerStatus"),
  visualQALedgerBody: document.getElementById("visualQALedgerBody"),
  refreshVisualBaselineComparison: document.getElementById("refreshVisualBaselineComparison"),
  createVisualBaselineComparison: document.getElementById("createVisualBaselineComparison"),
  visualBaselineComparisonStatus: document.getElementById("visualBaselineComparisonStatus"),
  visualBaselineComparisonBody: document.getElementById("visualBaselineComparisonBody"),
  refreshDemoArtifactCompleteness: document.getElementById("refreshDemoArtifactCompleteness"),
  createDemoArtifactCompleteness: document.getElementById("createDemoArtifactCompleteness"),
  demoArtifactCompletenessStatus: document.getElementById("demoArtifactCompletenessStatus"),
  demoArtifactCompletenessBody: document.getElementById("demoArtifactCompletenessBody"),
  refreshVisualEvidenceCapture: document.getElementById("refreshVisualEvidenceCapture"),
  createVisualEvidenceCapture: document.getElementById("createVisualEvidenceCapture"),
  visualEvidenceCaptureStatus: document.getElementById("visualEvidenceCaptureStatus"),
  visualEvidenceCaptureBody: document.getElementById("visualEvidenceCaptureBody"),
  refreshVisualEvidenceReviewDiff: document.getElementById("refreshVisualEvidenceReviewDiff"),
  createVisualEvidenceReviewDiff: document.getElementById("createVisualEvidenceReviewDiff"),
  visualEvidenceReviewDiffStatus: document.getElementById("visualEvidenceReviewDiffStatus"),
  visualEvidenceReviewDiffBody: document.getElementById("visualEvidenceReviewDiffBody"),
  refreshVisualEvidenceReviewAnnotations: document.getElementById("refreshVisualEvidenceReviewAnnotations"),
  createVisualEvidenceReviewAnnotations: document.getElementById("createVisualEvidenceReviewAnnotations"),
  visualEvidenceReviewAnnotationsStatus: document.getElementById("visualEvidenceReviewAnnotationsStatus"),
  visualEvidenceReviewAnnotationsBody: document.getElementById("visualEvidenceReviewAnnotationsBody"),
  refreshVisualEvidenceSignoffPacket: document.getElementById("refreshVisualEvidenceSignoffPacket"),
  createVisualEvidenceSignoffPacket: document.getElementById("createVisualEvidenceSignoffPacket"),
  visualEvidenceSignoffPacketStatus: document.getElementById("visualEvidenceSignoffPacketStatus"),
  visualEvidenceSignoffPacketBody: document.getElementById("visualEvidenceSignoffPacketBody"),
  refreshFinalReviewerLaunchChecklist: document.getElementById("refreshFinalReviewerLaunchChecklist"),
  createFinalReviewerLaunchChecklist: document.getElementById("createFinalReviewerLaunchChecklist"),
  finalReviewerLaunchChecklistStatus: document.getElementById("finalReviewerLaunchChecklistStatus"),
  finalReviewerLaunchChecklistBody: document.getElementById("finalReviewerLaunchChecklistBody"),
  refreshRecruiterDemoBrief: document.getElementById("refreshRecruiterDemoBrief"),
  createRecruiterDemoBrief: document.getElementById("createRecruiterDemoBrief"),
  recruiterDemoBriefStatus: document.getElementById("recruiterDemoBriefStatus"),
  recruiterDemoBriefBody: document.getElementById("recruiterDemoBriefBody"),
  refreshPublicPortfolioPackage: document.getElementById("refreshPublicPortfolioPackage"),
  createPublicPortfolioPackage: document.getElementById("createPublicPortfolioPackage"),
  publicPortfolioPackageStatus: document.getElementById("publicPortfolioPackageStatus"),
  publicPortfolioPackageBody: document.getElementById("publicPortfolioPackageBody"),
  refreshDemoReviewPlaybook: document.getElementById("refreshDemoReviewPlaybook"),
  createDemoReviewPlaybook: document.getElementById("createDemoReviewPlaybook"),
  demoReviewPlaybookStatus: document.getElementById("demoReviewPlaybookStatus"),
  demoReviewPlaybookBody: document.getElementById("demoReviewPlaybookBody"),
  refreshGithubPublicationBundle: document.getElementById("refreshGithubPublicationBundle"),
  createGithubPublicationBundle: document.getElementById("createGithubPublicationBundle"),
  githubPublicationBundleStatus: document.getElementById("githubPublicationBundleStatus"),
  githubPublicationBundleBody: document.getElementById("githubPublicationBundleBody"),
  refreshRepositoryPublicationQa: document.getElementById("refreshRepositoryPublicationQa"),
  createRepositoryPublicationQa: document.getElementById("createRepositoryPublicationQa"),
  repositoryPublicationQaStatus: document.getElementById("repositoryPublicationQaStatus"),
  repositoryPublicationQaBody: document.getElementById("repositoryPublicationQaBody"),
  refreshRepositoryExportHandoff: document.getElementById("refreshRepositoryExportHandoff"),
  createRepositoryExportHandoff: document.getElementById("createRepositoryExportHandoff"),
  repositoryExportHandoffStatus: document.getElementById("repositoryExportHandoffStatus"),
  repositoryExportHandoffBody: document.getElementById("repositoryExportHandoffBody"),
  refreshRepositoryDryRunReview: document.getElementById("refreshRepositoryDryRunReview"),
  createRepositoryDryRunReview: document.getElementById("createRepositoryDryRunReview"),
  repositoryDryRunReviewStatus: document.getElementById("repositoryDryRunReviewStatus"),
  repositoryDryRunReviewBody: document.getElementById("repositoryDryRunReviewBody"),
  refreshRepositoryFinalPackageReview: document.getElementById("refreshRepositoryFinalPackageReview"),
  createRepositoryFinalPackageReview: document.getElementById("createRepositoryFinalPackageReview"),
  repositoryFinalPackageReviewStatus: document.getElementById("repositoryFinalPackageReviewStatus"),
  repositoryFinalPackageReviewBody: document.getElementById("repositoryFinalPackageReviewBody"),
  refreshPublicReadmeCleanupReview: document.getElementById("refreshPublicReadmeCleanupReview"),
  createPublicReadmeCleanupReview: document.getElementById("createPublicReadmeCleanupReview"),
  publicReadmeCleanupReviewStatus: document.getElementById("publicReadmeCleanupReviewStatus"),
  publicReadmeCleanupReviewBody: document.getElementById("publicReadmeCleanupReviewBody"),
  refreshPublicRepositoryPolishPackage: document.getElementById("refreshPublicRepositoryPolishPackage"),
  createPublicRepositoryPolishPackage: document.getElementById("createPublicRepositoryPolishPackage"),
  publicRepositoryPolishPackageStatus: document.getElementById("publicRepositoryPolishPackageStatus"),
  publicRepositoryPolishPackageBody: document.getElementById("publicRepositoryPolishPackageBody"),
  refreshRepositoryExportChecklist: document.getElementById("refreshRepositoryExportChecklist"),
  createRepositoryExportChecklist: document.getElementById("createRepositoryExportChecklist"),
  repositoryExportChecklistStatus: document.getElementById("repositoryExportChecklistStatus"),
  repositoryExportChecklistBody: document.getElementById("repositoryExportChecklistBody"),
  refreshAnalysisProfiles: document.getElementById("refreshAnalysisProfiles"),
  analysisProfilesStatus: document.getElementById("analysisProfilesStatus"),
  analysisProfilesBody: document.getElementById("analysisProfilesBody"),
  runTransitProfile: document.getElementById("runTransitProfile"),
  runParkProfile: document.getElementById("runParkProfile"),
  refreshProfileWorkspaces: document.getElementById("refreshProfileWorkspaces"),
  profileRunnerStatus: document.getElementById("profileRunnerStatus"),
  profileWorkspacesBody: document.getElementById("profileWorkspacesBody"),
  refreshProductArchitecture: document.getElementById("refreshProductArchitecture"),
  productArchitectureStatus: document.getElementById("productArchitectureStatus"),
  productArchitectureBody: document.getElementById("productArchitectureBody"),
  refreshReleaseReadiness: document.getElementById("refreshReleaseReadiness"),
  createReleaseReadinessSnapshot: document.getElementById("createReleaseReadinessSnapshot"),
  releaseReadinessStatus: document.getElementById("releaseReadinessStatus"),
  releaseReadinessBody: document.getElementById("releaseReadinessBody"),
  refreshPortfolioDemo: document.getElementById("refreshPortfolioDemo"),
  createPortfolioDemoSnapshot: document.getElementById("createPortfolioDemoSnapshot"),
  portfolioDemoStatus: document.getElementById("portfolioDemoStatus"),
  portfolioDemoBody: document.getElementById("portfolioDemoBody"),
  refreshPortfolioEvidenceBundle: document.getElementById("refreshPortfolioEvidenceBundle"),
  createPortfolioEvidenceBundle: document.getElementById("createPortfolioEvidenceBundle"),
  portfolioEvidenceBundleStatus: document.getElementById("portfolioEvidenceBundleStatus"),
  portfolioEvidenceBundleBody: document.getElementById("portfolioEvidenceBundleBody"),
  refreshBundleReviewChecklist: document.getElementById("refreshBundleReviewChecklist"),
  createBundleReviewChecklist: document.getElementById("createBundleReviewChecklist"),
  bundleReviewChecklistStatus: document.getElementById("bundleReviewChecklistStatus"),
  bundleReviewChecklistBody: document.getElementById("bundleReviewChecklistBody"),
  refreshPortfolioNarrative: document.getElementById("refreshPortfolioNarrative"),
  createPortfolioNarrative: document.getElementById("createPortfolioNarrative"),
  portfolioNarrativeStatus: document.getElementById("portfolioNarrativeStatus"),
  portfolioNarrativeBody: document.getElementById("portfolioNarrativeBody"),
  refreshPortfolioHandoff: document.getElementById("refreshPortfolioHandoff"),
  createPortfolioHandoff: document.getElementById("createPortfolioHandoff"),
  portfolioHandoffStatus: document.getElementById("portfolioHandoffStatus"),
  portfolioHandoffBody: document.getElementById("portfolioHandoffBody"),
  refreshPortfolioEvidenceGallery: document.getElementById("refreshPortfolioEvidenceGallery"),
  createPortfolioEvidenceGallery: document.getElementById("createPortfolioEvidenceGallery"),
  portfolioEvidenceGalleryStatus: document.getElementById("portfolioEvidenceGalleryStatus"),
  portfolioEvidenceGalleryBody: document.getElementById("portfolioEvidenceGalleryBody"),
  refreshMultiPilotComparison: document.getElementById("refreshMultiPilotComparison"),
  createMultiPilotComparison: document.getElementById("createMultiPilotComparison"),
  multiPilotComparisonStatus: document.getElementById("multiPilotComparisonStatus"),
  multiPilotComparisonBody: document.getElementById("multiPilotComparisonBody"),
  refreshComparisonMapExports: document.getElementById("refreshComparisonMapExports"),
  createComparisonMapExport: document.getElementById("createComparisonMapExport"),
  comparisonMapExportsStatus: document.getElementById("comparisonMapExportsStatus"),
  comparisonMapExportsBody: document.getElementById("comparisonMapExportsBody"),
  profileDashboardSelect: document.getElementById("profileDashboardSelect"),
  refreshProfileDashboard: document.getElementById("refreshProfileDashboard"),
  profileDashboardStatus: document.getElementById("profileDashboardStatus"),
  profileDashboardBody: document.getElementById("profileDashboardBody"),
  refreshScoringRules: document.getElementById("refreshScoringRules"),
  scoringRulesStatus: document.getElementById("scoringRulesStatus"),
  scoringRulesBody: document.getElementById("scoringRulesBody"),
  refreshPostgisBackend: document.getElementById("refreshPostgisBackend"),
  createPostgisPlan: document.getElementById("createPostgisPlan"),
  postgisBackendStatus: document.getElementById("postgisBackendStatus"),
  postgisBackendBody: document.getElementById("postgisBackendBody"),
  refreshProfileMapper: document.getElementById("refreshProfileMapper"),
  createProfileMapperPlan: document.getElementById("createProfileMapperPlan"),
  profileMapperStatus: document.getElementById("profileMapperStatus"),
  profileMapperBody: document.getElementById("profileMapperBody"),
  refreshContractExecution: document.getElementById("refreshContractExecution"),
  createContractDryRun: document.getElementById("createContractDryRun"),
  contractExecutionStatus: document.getElementById("contractExecutionStatus"),
  contractExecutionBody: document.getElementById("contractExecutionBody"),
  refreshOsmTagQuality: document.getElementById("refreshOsmTagQuality"),
  runOsmTagQuality: document.getElementById("runOsmTagQuality"),
  osmTagQualityStatus: document.getElementById("osmTagQualityStatus"),
  osmTagQualityBody: document.getElementById("osmTagQualityBody"),
  refreshTemplateAuthoring: document.getElementById("refreshTemplateAuthoring"),
  createTemplateDraft: document.getElementById("createTemplateDraft"),
  templateAuthoringStatus: document.getElementById("templateAuthoringStatus"),
  templateAuthoringBody: document.getElementById("templateAuthoringBody"),
  refreshAuthoredProfileRunner: document.getElementById("refreshAuthoredProfileRunner"),
  runAuthoredProfile: document.getElementById("runAuthoredProfile"),
  enqueueAuthoredDraft: document.getElementById("enqueueAuthoredDraft"),
  authoredProfileRunnerStatus: document.getElementById("authoredProfileRunnerStatus"),
  authoredProfileRunnerBody: document.getElementById("authoredProfileRunnerBody"),
  refreshProfilePromotion: document.getElementById("refreshProfilePromotion"),
  createProfilePromotionProposal: document.getElementById("createProfilePromotionProposal"),
  approveProfilePromotionProposal: document.getElementById("approveProfilePromotionProposal"),
  rejectProfilePromotionProposal: document.getElementById("rejectProfilePromotionProposal"),
  createProfileContractDiff: document.getElementById("createProfileContractDiff"),
  createProfileApplicationPlan: document.getElementById("createProfileApplicationPlan"),
  createProfileConfigApplyProposal: document.getElementById("createProfileConfigApplyProposal"),
  createProfileRegressionPreview: document.getElementById("createProfileRegressionPreview"),
  profilePromotionStatus: document.getElementById("profilePromotionStatus"),
  profilePromotionBody: document.getElementById("profilePromotionBody"),
  refreshExecutionQueue: document.getElementById("refreshExecutionQueue"),
  enqueueExecutionQueueJob: document.getElementById("enqueueExecutionQueueJob"),
  executionQueueStatus: document.getElementById("executionQueueStatus"),
  executionQueueBody: document.getElementById("executionQueueBody"),
  refreshDatasetPackages: document.getElementById("refreshDatasetPackages"),
  createDatasetPackage: document.getElementById("createDatasetPackage"),
  datasetPackagesStatus: document.getElementById("datasetPackagesStatus"),
  datasetPackagesBody: document.getElementById("datasetPackagesBody"),
  pilotSearch: document.getElementById("pilotSearch"),
  pilotAreaSelect: document.getElementById("pilotAreaSelect"),
  pilotRouteAware: document.getElementById("pilotRouteAware"),
  buildPilotWorkspace: document.getElementById("buildPilotWorkspace"),
  pilotStatus: document.getElementById("pilotStatus"),
  pilotPreflight: document.getElementById("pilotPreflight"),
  planAnalysisWorkflow: document.getElementById("planAnalysisWorkflow"),
  startAnalysisWorkflow: document.getElementById("startAnalysisWorkflow"),
  analysisWorkflowStatus: document.getElementById("analysisWorkflowStatus"),
  analysisWorkflowBody: document.getElementById("analysisWorkflowBody"),
  refreshAnalysisRuns: document.getElementById("refreshAnalysisRuns"),
  analysisRunsStatus: document.getElementById("analysisRunsStatus"),
  analysisRunsBody: document.getElementById("analysisRunsBody"),
  generatePortfolioReport: document.getElementById("generatePortfolioReport"),
  generateTransitPortfolioReport: document.getElementById("generateTransitPortfolioReport"),
  generateParkPortfolioReport: document.getElementById("generateParkPortfolioReport"),
  generateProfileComparisonReport: document.getElementById("generateProfileComparisonReport"),
  generateProfileExportBundle: document.getElementById("generateProfileExportBundle"),
  comparePortfolioRuns: document.getElementById("comparePortfolioRuns"),
  refreshPortfolioReports: document.getElementById("refreshPortfolioReports"),
  portfolioReportsStatus: document.getElementById("portfolioReportsStatus"),
  portfolioReportsBody: document.getElementById("portfolioReportsBody"),
  refreshJobs: document.getElementById("refreshJobs"),
  jobStatus: document.getElementById("jobStatus"),
  jobHistory: document.getElementById("jobHistory"),
  sourceHint: document.getElementById("sourceHint"),
  buildWorkspace: document.getElementById("buildWorkspace"),
  buildGenericWorkspace: document.getElementById("buildGenericWorkspace"),
  buildRouteAwareWorkspace: document.getElementById("buildRouteAwareWorkspace"),
  buildStatus: document.getElementById("buildStatus"),
  workspaceStatus: document.getElementById("workspaceStatus"),
  workspaceRegistry: document.getElementById("workspaceRegistry"),
  architectureStatus: document.getElementById("architectureStatus"),
  productArchitecturePanel: document.getElementById("productArchitecturePanel"),
  profileResultsStatus: document.getElementById("profileResultsStatus"),
  profileResultRows: document.getElementById("profileResultRows"),
  profileStatus: document.getElementById("profileStatus"),
  templateStatus: document.getElementById("templateStatus"),
  sourceProfile: document.getElementById("sourceProfile"),
  templateReadiness: document.getElementById("templateReadiness"),
  metrics: document.getElementById("metrics"),
  reviewWording: document.getElementById("reviewWording"),
  generatorType: document.getElementById("generatorType"),
  minScore: document.getElementById("minScore"),
  minScoreValue: document.getElementById("minScoreValue"),
  noCrossing: document.getElementById("noCrossing"),
  majorRoad: document.getElementById("majorRoad"),
  map: document.getElementById("map"),
  rows: document.getElementById("candidateRows"),
  detail: document.getElementById("candidateDetail"),
  exportCsv: document.getElementById("exportCsv"),
  tabSetup: document.getElementById("tabSetup"),
  tabReview: document.getElementById("tabReview"),
  tabReports: document.getElementById("tabReports"),
  mapPanel: document.getElementById("mapPanel"),
  mapCanvas: document.getElementById("mapCanvas"),
};

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmt(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "";
  const num = Number(value);
  if (Number.isFinite(num)) return `${num.toFixed(1)}${suffix}`;
  return `${value}${suffix}`;
}

function typeLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function flagPills(flags) {
  return (Array.isArray(flags) ? flags : [])
    .map((flag) => `<span class="pill">${escapeHtml(flag)}</span>`)
    .join("");
}

function dashboardBase() {
  return `/api/dashboard-workspaces/${encodeURIComponent(state.activeWorkspaceId)}`;
}

function bounds(points) {
  const valid = points.filter((p) => Number.isFinite(p.lon) && Number.isFinite(p.lat));
  const xs = valid.map((p) => p.lon);
  const ys = valid.map((p) => p.lat);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function project(point, b, width, height) {
  // Uniform-scale Web-Mercator fit into width x height (preserves geographic
  // proportions, unlike an independent per-axis stretch).
  const pad = 24;
  const lon2x = (lon) => (lon * Math.PI) / 180;
  const lat2y = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const minX = lon2x(b.minX);
  const minY = lat2y(b.minY);
  const spanX = lon2x(b.maxX) - minX || 1;
  const spanY = lat2y(b.maxY) - minY || 1;
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const offX = (width - scale * spanX) / 2;
  const offY = (height - scale * spanY) / 2;
  return {
    x: offX + (lon2x(point.lon) - minX) * scale,
    y: height - offY - (lat2y(point.lat) - minY) * scale,
  };
}

function updateOverviewDeck(counts, route) {
  if (els.overviewGeneratorCount) {
    els.overviewGeneratorCount.textContent = counts.pedestrian_generators ?? "--";
  }
  if (els.overviewCrossingCount) {
    els.overviewCrossingCount.textContent = counts.crossings ?? "--";
  }
  if (els.overviewMajorRoadCount) {
    els.overviewMajorRoadCount.textContent = counts.major_roads ?? "--";
  }
  if (els.overviewValidationStatus) {
    els.overviewValidationStatus.textContent = state.summary.validation_passed ? "passed" : "check";
  }
}

function setupControlVisibility() {
  if (!els.controlPanel) {
    return;
  }
  const primary = new Set([
    "Workspace",
    "Pilot Area",
    "Create Analysis",
    "Candidate Filters",
    "Metrics",
    "Interpretation",
  ]);
  for (const section of els.controlPanel.querySelectorAll("section")) {
    const heading = section.querySelector("h2");
    const title = heading ? heading.textContent.trim() : "";
    section.classList.toggle("priority-control", primary.has(title));
    section.classList.toggle("advanced-control", !primary.has(title));
  }
  if (els.showAdvancedControls) {
    els.controlPanel.classList.toggle("show-advanced", els.showAdvancedControls.checked);
  }
}

function renderMetrics() {
  const counts = state.summary.counts;
  const route = state.summary.route_aware_analysis || {};
  const rows = [
    ["Generators", counts.pedestrian_generators],
    ["Crossings", counts.crossings],
    ["Traffic signals", counts.traffic_signals],
    ["Road segments", counts.road_segments],
    ["Major roads", counts.major_roads],
    ["Route median", route.median_route_nearest_crossing_m ? `${route.median_route_nearest_crossing_m} m` : "n/a"],
    ["Route >250 m", route.generators_route_over_250m ?? "n/a"],
    ["Validation", state.summary.validation_passed ? "passed" : "check"],
  ];
  els.metrics.innerHTML = rows
    .map(([label, value]) => `<div class="metric"><span>${label}</span><b>${value}</b></div>`)
    .join("");
  els.reviewWording.textContent = state.summary.review_wording;
  updateOverviewDeck(counts, route);
}

function populateFilters() {
  const types = Object.keys(state.summary.generator_types).sort();
  els.generatorType.innerHTML = `<option value="">All</option>${types
    .map((kind) => `<option value="${escapeHtml(kind)}">${escapeHtml(typeLabel(kind))}</option>`)
    .join("")}`;
}

function populateCatalogControls() {
  els.sourceSelect.innerHTML = state.sources
    .map((source) => `<option value="${escapeHtml(source.dataset_id)}">${escapeHtml(source.file_name)}</option>`)
    .join("");
  els.templateSelect.innerHTML = state.templates
    .map((template) => `<option value="${escapeHtml(template.template_id)}">${escapeHtml(template.name)}</option>`)
    .join("");
  const firstSource = state.sources[0];
  els.sourceHint.textContent = firstSource
    ? `${firstSource.profile_status}; ${firstSource.layer_count} layers; ${firstSource.size_mb.toFixed(1)} MB`
    : "No local sources found.";
}

function renderScoringRules() {
  const overview = state.scoringRules;
  const audit = state.scoringAudit;
  if (!overview || !audit) {
    els.scoringRulesStatus.textContent = "No scoring audit loaded.";
    els.scoringRulesBody.innerHTML = "";
    return;
  }
  if (overview.error || audit.error) {
    els.scoringRulesStatus.textContent = `Scoring rules failed: ${overview.error || audit.error}`;
    els.scoringRulesBody.innerHTML = `<p class="note">Scoring rule evidence is unavailable.</p>`;
    return;
  }
  els.scoringRulesStatus.textContent = `${audit.profile_id}: ${audit.exact_match_count}/${audit.rows_audited} exact score matches`;
  const profileCards = (overview.profiles || [])
    .map((profile) => `
      <div class="workspace-card">
        <h3>${escapeHtml(profile.profile_id)}</h3>
        <p><b>Score field:</b> ${escapeHtml(profile.score_field)}</p>
        <p><b>Rules:</b> ${profile.scoring_rule_count}; <b>Context:</b> ${profile.context_rule_count}</p>
      </div>
    `)
    .join("");
  const sampleRows = (audit.rows || [])
    .map((row) => `
      <div class="workspace-card">
        <h3>${escapeHtml(row.result_id)} - ${escapeHtml(row.status)}</h3>
        <p><b>Actual:</b> ${row.actual_score}; <b>Expected:</b> ${row.expected_score}; <b>Delta:</b> ${row.delta}</p>
        <p><b>Rules:</b> ${escapeHtml((row.active_rule_ids || []).join(", "))}</p>
      </div>
    `)
    .join("");
  els.scoringRulesBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(overview.scoring_rules_version)}</h3>
      <p>${escapeHtml(overview.scoring_policy || "")}</p>
      <p><b>Mismatches:</b> ${audit.mismatch_count}; <b>Max delta:</b> ${audit.max_abs_delta}</p>
    </div>
    ${profileCards}
    ${sampleRows}
  `;
}

function renderPostgisBackend() {
  const payload = state.postgisBackend;
  if (!payload) {
    els.postgisBackendStatus.textContent = "No PostGIS plan loaded.";
    els.postgisBackendBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const readiness = status.readiness || {};
  const schema = payload.schema || {};
  const plan = state.postgisPlan || payload.plan || {};
  const blockers = readiness.blockers || [];
  els.postgisBackendStatus.textContent = `${readiness.readiness_level || "planning"}; ${schema.table_count || 0} tables`;
  els.postgisBackendBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.mode || "planning")}</h3>
      <p><b>Connection:</b> ${escapeHtml(status.connection_status || "")}</p>
      <p><b>Schema:</b> ${escapeHtml(schema.schema_version || "")}; <b>Indexes:</b> ${schema.index_count || 0}</p>
      <p><b>Rows:</b> ${readiness.profile_result_rows || 0}; <b>Workspaces:</b> ${readiness.workspace_count || 0}</p>
      <p><b>Blockers:</b> ${escapeHtml(blockers.join(", ") || "none")}</p>
    </div>
    <div class="workspace-card">
      <h3>Migration plan</h3>
      <p><b>Plan:</b> ${escapeHtml(plan.plan_id || "preview")}</p>
      <p><b>Phases:</b> ${(plan.phases || []).length}; <b>Scope:</b> ${escapeHtml(plan.scope || "")}</p>
      <p><b>Next:</b> ${escapeHtml(readiness.recommended_next_action || "")}</p>
    </div>
  `;
}

function renderProfileMapper() {
  const payload = state.profileMapper;
  if (!payload) {
    els.profileMapperStatus.textContent = "No profile mapper contracts loaded.";
    els.profileMapperBody.innerHTML = "";
    return;
  }
  const overview = payload.overview || {};
  const compatibility = payload.compatibility || {};
  const plan = state.profileMapperPlan || payload.plan || {};
  const rows = compatibility.rows || [];
  els.profileMapperStatus.textContent = `${overview.contract_count || 0} contracts; ${compatibility.compatible_contract_count || 0} compatible`;
  const cards = rows
    .map((row) => `
      <div class="workspace-card">
        <h3>${escapeHtml(row.profile_id)}</h3>
        <p><b>Status:</b> ${escapeHtml(row.contract_status || "")}; <b>Can plan:</b> ${row.can_plan ? "yes" : "no"}</p>
        <p><b>Required:</b> ${escapeHtml((row.required_groups || []).join(", ") || "none")}</p>
        <p><b>Blockers:</b> ${escapeHtml((row.blockers || []).join(", ") || "none")}</p>
      </div>
    `)
    .join("");
  els.profileMapperBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(overview.profile_mapper_contracts_version || "")}</h3>
      <p>${escapeHtml(overview.contract_policy || "")}</p>
      <p><b>Implemented:</b> ${overview.implemented_contract_count || 0}; <b>Ready/planned:</b> ${overview.ready_or_implemented_contract_count || 0}</p>
      <p><b>Plan:</b> ${escapeHtml(plan.plan_id || "preview")}; <b>Profile:</b> ${escapeHtml(plan.profile_id || "")}</p>
    </div>
    ${cards}
  `;
}

function renderContractExecution() {
  const payload = state.contractExecution;
  if (!payload) {
    els.contractExecutionStatus.textContent = "No contract execution dry run loaded.";
    els.contractExecutionBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const dryRun = state.contractDryRun || payload.dryRun || {};
  const adapters = status.adapters || [];
  els.contractExecutionStatus.textContent = `${status.executable_now_count || 0}/${status.adapter_count || 0} adapters executable now`;
  const cards = adapters
    .map((adapter) => `
      <div class="workspace-card">
        <h3>${escapeHtml(adapter.profile_id)}</h3>
        <p><b>Adapter:</b> ${escapeHtml(adapter.adapter_id || "")}</p>
        <p><b>Status:</b> ${escapeHtml(adapter.execution_status || "")}</p>
        <p><b>Entrypoint:</b> ${escapeHtml(adapter.backend_entrypoint || "planned")}</p>
      </div>
    `)
    .join("");
  els.contractExecutionBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.contract_execution_version || "")}</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Dry run:</b> ${escapeHtml(dryRun.dry_run_id || "preview")}; <b>Can execute:</b> ${dryRun.can_execute_now ? "yes" : "no"}</p>
      <p><b>Would call:</b> ${escapeHtml(dryRun.would_call || "")}</p>
    </div>
    ${cards}
  `;
}

function renderPilotAreas() {
  if (!state.pilots.length) {
    els.pilotAreaSelect.innerHTML = `<option value="">No matching pilot areas</option>`;
    els.pilotStatus.textContent = state.pilotMetadata
      ? `${state.pilotMetadata.pilot_count} catalog areas; no current match`
      : "Pilot catalog unavailable";
    state.pilotPreflight = null;
    renderPilotPreflight();
    return;
  }
  els.pilotAreaSelect.innerHTML = state.pilots
    .map((pilot) => {
      const pop = Number(pilot.population || 0).toLocaleString();
      return `<option value="${escapeHtml(pilot.osm_id)}">${escapeHtml(pilot.name)} - ${escapeHtml(pilot.fclass)} - ${pop}</option>`;
    })
    .join("");
  const metaText = state.pilotMetadata ? `${state.pilotMetadata.pilot_count} catalog areas` : "catalog ready";
  els.pilotStatus.textContent = `${state.pilots.length} shown; ${metaText}`;
}

function selectedPilot() {
  return state.pilots.find((pilot) => pilot.osm_id === els.pilotAreaSelect.value) || null;
}

function chooseDefaultWorkspace() {
  if (!state.workspaces.length) return "";
  const preferred = state.workspaces.find((workspace) => workspace.workspace_id === DEFAULT_DASHBOARD_WORKSPACE_ID);
  return (preferred || state.workspaces[state.workspaces.length - 1]).workspace_id;
}

function populateDashboardWorkspaceSelect() {
  if (!state.workspaces.length) {
    els.dashboardWorkspaceSelect.innerHTML = `<option value="">No generated workspaces</option>`;
    state.activeWorkspaceId = "";
    return;
  }
  if (!state.activeWorkspaceId || !state.workspaces.some((workspace) => workspace.workspace_id === state.activeWorkspaceId)) {
    state.activeWorkspaceId = chooseDefaultWorkspace();
  }
  els.dashboardWorkspaceSelect.innerHTML = state.workspaces
    .map((workspace) => `<option value="${escapeHtml(workspace.workspace_id)}">${escapeHtml(workspace.workspace_id)}</option>`)
    .join("");
  els.dashboardWorkspaceSelect.value = state.activeWorkspaceId;
}

function candidateQuery() {
  const params = new URLSearchParams();
  params.set("limit", "150");
  params.set("min_score", els.minScore.value);
  if (els.generatorType.value) params.set("generator_type", els.generatorType.value);
  if (els.noCrossing.checked) params.set("no_crossing_150m", "true");
  if (els.majorRoad.checked) params.set("major_road_150m", "true");
  return params.toString();
}

async function loadCandidates() {
  if (!state.activeWorkspaceId) return;
  els.minScoreValue.textContent = els.minScore.value;
  state.candidates = await getJson(`${dashboardBase()}/candidates?${candidateQuery()}`);
  renderTable();
  renderMap();
  const selectedStillVisible = state.selected && state.candidates.some((row) => row.generator_id === state.selected.generator_id);
  if (selectedStillVisible) {
    selectCandidate(state.selected.generator_id);
  } else if (state.candidates.length) {
    selectCandidate(state.candidates[0].generator_id);
  }
}

const REVIEW_STATUS_LABELS = [
  ["unreviewed", "Unreviewed"],
  ["to_review", "To review"],
  ["reviewed", "Reviewed"],
  ["dismissed", "Dismissed"],
];

async function loadReviewDecisions() {
  try {
    const data = await getJson(`${dashboardBase()}/review-decisions`);
    const map = {};
    for (const decision of data.decisions || []) {
      map[decision.generator_id] = decision;
    }
    state.decisions = map;
    state.decisionSummary = data.summary || null;
  } catch (err) {
    state.decisions = {};
    state.decisionSummary = null;
  }
}

function reviewStatusDot(generatorId) {
  const decision = state.decisions[generatorId];
  const status = decision && decision.status ? decision.status : "unreviewed";
  if (status === "unreviewed") {
    return "";
  }
  return `<span class="rev-dot rev-${status}" title="Review status: ${status.replace("_", " ")}"></span>`;
}

async function saveReviewDecision(generatorId) {
  const statusEl = document.getElementById("reviewStatus");
  if (!statusEl) return;
  const noteEl = document.getElementById("reviewNote");
  const assigneeEl = document.getElementById("reviewAssignee");
  try {
    const result = await postJson(`${dashboardBase()}/review-decisions`, {
      generator_id: generatorId,
      status: statusEl.value,
      note: noteEl ? noteEl.value : "",
      assignee: assigneeEl ? assigneeEl.value : "",
    });
    state.decisions[generatorId] = result.decision;
    await loadReviewDecisions();
    selectCandidate(generatorId);
    els.status.textContent = `Review state saved for ${generatorId}`;
  } catch (err) {
    els.status.textContent = `Review save failed: ${err.message}`;
  }
}

async function loadDashboardWorkspace() {
  if (!state.activeWorkspaceId) {
    els.status.textContent = "No workspace selected";
    return;
  }
  state.summary = await getJson(`${dashboardBase()}/summary`);
  state.features = await getJson(`${dashboardBase()}/map-features`);
  if (state.summary.error || state.features.error) {
    els.status.textContent = "Workspace load failed";
    els.detail.textContent = state.summary.error || state.features.error;
    return;
  }
  renderMetrics();
  populateFilters();
  await loadReviewDecisions();
  await loadCandidates();
  els.status.textContent = `Dashboard: ${state.activeWorkspaceId}`;
}

async function loadSourceProfile() {
  const datasetId = els.sourceSelect.value;
  if (!datasetId) return;
  state.sourceProfile = await getJson(`/api/catalog/sources/${datasetId}`);
  renderSourceProfile();
  await loadTemplateCheck();
  await loadPilotPreflight();
}

async function loadTemplateCheck() {
  const datasetId = els.sourceSelect.value;
  const templateId = els.templateSelect.value || "safe_access";
  if (!datasetId) return;
  state.templateCheck = await getJson(`/api/templates/${templateId}/check?dataset_id=${datasetId}`);
  renderTemplateCheck();
}

async function loadSourceOnboarding() {
  state.sourceOnboarding = {
    status: await getJson("/api/source-onboarding"),
    sources: await getJson("/api/source-onboarding/sources"),
  };
  renderSourceOnboarding();
}

async function refreshSourceOnboarding() {
  els.sourceOnboardingStatus.textContent = "Scanning local source folder...";
  const result = await postJson("/api/source-onboarding/refresh", {});
  if (!result.ok) {
    els.sourceOnboardingStatus.textContent = `Source scan failed: ${result.error || "unknown error"}`;
    return;
  }
  await loadSourceOnboarding();
  await loadLocalIntake();
  await loadAnalysisProfiles();
}

async function loadLocalIntake() {
  state.localIntake = {
    status: await getJson("/api/local-intake"),
    sources: await getJson("/api/local-intake/sources"),
  };
  renderLocalIntake();
}

function localIntakePayload() {
  const path = els.localIntakePath.value.trim();
  if (path) return { path };
  return { dataset_id: els.sourceSelect.value };
}

async function previewLocalIntake() {
  els.localIntakeStatus.textContent = "Previewing selected local source...";
  const result = await postJson("/api/local-intake/preview", localIntakePayload());
  state.localIntakePreview = result;
  if (result.error) {
    els.localIntakeStatus.textContent = `Preview failed: ${result.error}`;
  }
  renderLocalIntake();
}

async function createLocalIntakePlan() {
  els.localIntakeStatus.textContent = "Creating metadata intake plan...";
  const result = await postJson("/api/local-intake/plan", localIntakePayload());
  state.localIntakePlan = result;
  state.localIntakePreview = result.source_preview || state.localIntakePreview;
  if (result.error) {
    els.localIntakeStatus.textContent = `Plan failed: ${result.error}`;
  }
  renderLocalIntake();
}


async function loadSourceImportGuardrails() {
  state.sourceImportGuardrails = {
    status: await getJson("/api/source-import-guardrails"),
    requests: await getJson("/api/source-import-guardrails/requests?limit=5"),
  };
  renderSourceImportGuardrails();
}

function sourceImportPayload() {
  const payload = localIntakePayload();
  payload.template_id = els.templateSelect.value || "safe_access";
  return payload;
}

async function previewSourceImportGuardrails() {
  els.sourceImportGuardrailsStatus.textContent = "Checking source import guardrails...";
  const result = await postJson("/api/source-import-guardrails/preview", sourceImportPayload());
  state.sourceImportPreview = result;
  if (result.error) {
    els.sourceImportGuardrailsStatus.textContent = `Guardrail preview failed: ${result.error}`;
  }
  renderSourceImportGuardrails();
}

async function createSourceImportReview() {
  els.sourceImportGuardrailsStatus.textContent = "Creating source import review packet...";
  const payload = sourceImportPayload();
  payload.created_by = "dashboard";
  payload.notes = "Dashboard-created v053 source import review packet.";
  const result = await postJson("/api/source-import-guardrails/request", payload);
  state.sourceImportRequest = result.request || null;
  state.sourceImportPreview = result.request ? result.request.preview : state.sourceImportPreview;
  if (result.error) {
    els.sourceImportGuardrailsStatus.textContent = `Review packet failed: ${result.error}`;
  }
  await loadSourceImportGuardrails();
}

async function approveSourceImportReview() {
  const request = state.sourceImportRequest || ((state.sourceImportGuardrails && state.sourceImportGuardrails.requests && state.sourceImportGuardrails.requests[0]) || null);
  if (!request || !request.request_id) {
    els.sourceImportGuardrailsStatus.textContent = "Create a review packet before approving.";
    return;
  }
  els.sourceImportGuardrailsStatus.textContent = "Recording source import approval...";
  const result = await postJson(`/api/source-import-guardrails/requests/${encodeURIComponent(request.request_id)}/decision`, {
    decision: "approve",
    reviewer: "dashboard",
    approval_phrase: "approve metadata-only import",
    source_files_read_only_ack: true,
    generated_outputs_only_ack: true,
    no_browser_upload_ack: true,
    claim_boundary_ack: true,
    notes: "Dashboard approval for metadata-only local source import handoff.",
  });
  state.sourceImportDecision = result.decision || null;
  if (result.error) {
    els.sourceImportGuardrailsStatus.textContent = `Approval failed: ${result.error}`;
  }
  await loadSourceImportGuardrails();
}

async function loadSourceHandoff() {
  state.sourceHandoff = {
    status: await getJson("/api/source-handoff"),
    candidates: await getJson("/api/source-handoff/candidates?limit=5"),
    handoffs: await getJson("/api/source-handoff/handoffs?limit=5"),
  };
  renderSourceHandoff();
}

async function createSourceHandoff() {
  els.sourceHandoffStatus.textContent = "Creating planned source handoff...";
  const candidate = state.sourceHandoff && state.sourceHandoff.candidates && state.sourceHandoff.candidates[0];
  const payload = {
    request_id: candidate ? candidate.request_id : "",
    profile_id: "safe_access_pedestrian_review",
    pilot_osm_id: "53796999",
    target_workspace_id: "source_handoff_safe_access_v001",
    created_by: "dashboard",
  };
  const result = await postJson("/api/source-handoff/create", payload);
  state.sourceHandoffCreated = result.handoff || null;
  if (result.error) {
    els.sourceHandoffStatus.textContent = `Source handoff failed: ${result.error}`;
  }
  await loadSourceHandoff();
}

async function loadSourceHandoffExecution() {
  state.sourceHandoffExecution = {
    status: await getJson("/api/source-handoff-execution"),
    candidates: await getJson("/api/source-handoff-execution/candidates?limit=5"),
    executions: await getJson("/api/source-handoff-execution/executions?limit=5"),
  };
  renderSourceHandoffExecution();
}

async function executeSourceHandoff() {
  els.sourceHandoffExecutionStatus.textContent = "Executing approved source handoff...";
  const candidate = state.sourceHandoffExecution && state.sourceHandoffExecution.candidates && state.sourceHandoffExecution.candidates[0];
  const payload = {
    handoff_id: candidate ? candidate.handoff_id : "",
    execution_ack: "execute approved handoff",
    source_files_read_only_ack: true,
    generated_outputs_only_ack: true,
    claim_boundary_ack: true,
    compare_outputs_ack: true,
    route_aware: false,
    created_by: "dashboard",
  };
  const result = await postJson("/api/source-handoff-execution/execute", payload);
  state.sourceHandoffExecutionCreated = result.execution || null;
  if (result.error) {
    els.sourceHandoffExecutionStatus.textContent = `Source handoff execution failed: ${result.error}`;
  }
  await loadSourceHandoffExecution();
}

async function loadExecutionEvidencePackage() {
  state.executionEvidencePackage = {
    status: await getJson("/api/execution-evidence-package"),
    candidates: await getJson("/api/execution-evidence-package/candidates?limit=5"),
    packages: await getJson("/api/execution-evidence-package/packages?limit=5"),
  };
  renderExecutionEvidencePackage();
}

async function createExecutionEvidencePackage() {
  els.executionEvidencePackageStatus.textContent = "Creating execution evidence package...";
  const candidate = state.executionEvidencePackage && state.executionEvidencePackage.candidates && state.executionEvidencePackage.candidates[0];
  const payload = {
    execution_id: candidate ? candidate.execution_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v059 execution evidence package.",
  };
  const result = await postJson("/api/execution-evidence-package/create", payload);
  state.executionEvidencePackageCreated = result.package || null;
  if (result.error) {
    els.executionEvidencePackageStatus.textContent = `Execution evidence package failed: ${result.error}`;
  }
  await loadExecutionEvidencePackage();
}

async function loadExecutionResultDiff() {
  state.executionResultDiff = {
    status: await getJson("/api/execution-result-diff"),
    candidates: await getJson("/api/execution-result-diff/candidates?limit=5"),
    diffs: await getJson("/api/execution-result-diff/diffs?limit=5"),
  };
  renderExecutionResultDiff();
}

async function createExecutionResultDiff() {
  els.executionResultDiffStatus.textContent = "Creating execution result diff...";
  const candidate = state.executionResultDiff && state.executionResultDiff.candidates && state.executionResultDiff.candidates[0];
  const payload = {
    left_package_id: candidate ? candidate.left_package_id : "",
    right_package_id: candidate ? candidate.right_package_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v059 execution result diff.",
  };
  const result = await postJson("/api/execution-result-diff/create", payload);
  state.executionResultDiffCreated = result.diff || null;
  if (result.error) {
    els.executionResultDiffStatus.textContent = `Execution result diff failed: ${result.error}`;
  }
  await loadExecutionResultDiff();
}

async function loadExecutionDiffGallery() {
  state.executionDiffGallery = {
    status: await getJson("/api/execution-diff-gallery"),
    items: await getJson("/api/execution-diff-gallery/items?limit=8"),
    galleries: await getJson("/api/execution-diff-gallery/galleries?limit=5"),
  };
  renderExecutionDiffGallery();
}

async function createExecutionDiffGallery() {
  els.executionDiffGalleryStatus.textContent = "Creating execution diff gallery...";
  const result = await postJson("/api/execution-diff-gallery/create", {
    created_by: "dashboard",
    notes: "Dashboard-created v059 execution diff gallery.",
    limit: 50,
  });
  state.executionDiffGalleryCreated = result.gallery || null;
  if (result.error) {
    els.executionDiffGalleryStatus.textContent = `Execution diff gallery failed: ${result.error}`;
  }
  await loadExecutionDiffGallery();
}

async function loadExecutionDiffDetail() {
  state.executionDiffDetail = {
    status: await getJson("/api/execution-diff-detail"),
    baselines: await getJson("/api/execution-diff-detail/baselines?limit=5"),
    drilldowns: await getJson("/api/execution-diff-detail/drilldowns?limit=5"),
  };
  renderExecutionDiffDetail();
}

async function createExecutionDiffDetail() {
  els.executionDiffDetailStatus.textContent = "Creating execution diff detail drilldown...";
  const baseline = state.executionDiffDetail && state.executionDiffDetail.baselines && state.executionDiffDetail.baselines[0];
  const result = await postJson("/api/execution-diff-detail/create", {
    diff_id: baseline ? baseline.diff_id : "",
    baseline_diff_id: baseline ? baseline.diff_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v059 execution diff detail drilldown.",
  });
  state.executionDiffDetailCreated = result.detail || null;
  if (result.error) {
    els.executionDiffDetailStatus.textContent = `Execution diff detail failed: ${result.error}`;
  }
  await loadExecutionDiffDetail();
}

async function loadReproducibilityAuditPacket() {
  state.reproducibilityAuditPacket = {
    status: await getJson("/api/reproducibility-audit-packet"),
    candidates: await getJson("/api/reproducibility-audit-packet/candidates?limit=5"),
    packets: await getJson("/api/reproducibility-audit-packet/packets?limit=5"),
  };
  renderReproducibilityAuditPacket();
}

async function createReproducibilityAuditPacket() {
  els.reproducibilityAuditPacketStatus.textContent = "Creating reproducibility audit packet...";
  const candidate = state.reproducibilityAuditPacket && state.reproducibilityAuditPacket.candidates && state.reproducibilityAuditPacket.candidates[0];
  const result = await postJson("/api/reproducibility-audit-packet/create", {
    detail_id: candidate ? candidate.detail_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v059 reproducibility audit packet.",
  });
  state.reproducibilityAuditPacketCreated = result.packet || null;
  if (result.error) {
    els.reproducibilityAuditPacketStatus.textContent = `Reproducibility audit packet failed: ${result.error}`;
  }
  await loadReproducibilityAuditPacket();
}

async function loadReviewerAuditIndex() {
  state.reviewerAuditIndex = {
    status: await getJson("/api/reviewer-audit-index"),
    indexes: await getJson("/api/reviewer-audit-index/indexes?limit=5"),
  };
  renderReviewerAuditIndex();
}

async function createReviewerAuditIndex() {
  els.reviewerAuditIndexStatus.textContent = "Creating reviewer audit index...";
  const result = await postJson("/api/reviewer-audit-index/create", {
    created_by: "dashboard",
    notes: "Dashboard-created v067 reviewer audit index.",
    packet_limit: 25,
  });
  state.reviewerAuditIndexCreated = result.index || null;
  if (result.error) {
    els.reviewerAuditIndexStatus.textContent = `Reviewer audit index failed: ${result.error}`;
  }
  await loadReviewerAuditIndex();
}

async function loadPortfolioExportLauncher() {
  state.portfolioExportLauncher = {
    status: await getJson("/api/portfolio-export-launcher"),
    launchers: await getJson("/api/portfolio-export-launcher/launchers?limit=5"),
  };
  renderPortfolioExportLauncher();
}

async function createPortfolioExportLauncher() {
  els.portfolioExportLauncherStatus.textContent = "Creating portfolio export launcher...";
  const result = await postJson("/api/portfolio-export-launcher/create", {
    created_by: "dashboard",
    notes: "Dashboard-created v067 portfolio export launcher.",
    target_limit: 25,
  });
  state.portfolioExportLauncherCreated = result.launcher || null;
  if (result.error) {
    els.portfolioExportLauncherStatus.textContent = `Portfolio export launcher failed: ${result.error}`;
  }
  await loadPortfolioExportLauncher();
}

async function loadPortableReleasePackage() {
  state.portableReleasePackage = {
    status: await getJson("/api/portable-release-package"),
    packages: await getJson("/api/portable-release-package/packages?limit=5"),
  };
  renderPortableReleasePackage();
}

async function createPortableReleasePackage() {
  els.portableReleasePackageStatus.textContent = "Creating portable release package...";
  const launcher = state.portfolioExportLauncher && state.portfolioExportLauncher.launchers && state.portfolioExportLauncher.launchers[0];
  const result = await postJson("/api/portable-release-package/create", {
    launcher_id: launcher ? launcher.launcher_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v067 portable release package.",
    target_limit: 30,
  });
  state.portableReleasePackageCreated = result.package || null;
  if (result.error) {
    els.portableReleasePackageStatus.textContent = `Portable release package failed: ${result.error}`;
  }
  await loadPortableReleasePackage();
}

async function loadDemoScriptPack() {
  state.demoScriptPack = {
    status: await getJson("/api/demo-script-pack"),
    packs: await getJson("/api/demo-script-pack/packs?limit=5"),
  };
  renderDemoScriptPack();
}

async function createDemoScriptPack() {
  els.demoScriptPackStatus.textContent = "Creating demo script pack...";
  const portablePackage = state.portableReleasePackage && state.portableReleasePackage.packages && state.portableReleasePackage.packages[0];
  const result = await postJson("/api/demo-script-pack/create", {
    package_id: portablePackage ? portablePackage.package_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v067 demo script pack.",
  });
  state.demoScriptPackCreated = result.pack || null;
  if (result.error) {
    els.demoScriptPackStatus.textContent = `Demo script pack failed: ${result.error}`;
  }
  await loadDemoScriptPack();
}

async function loadVisualQALedger() {
  state.visualQALedger = {
    status: await getJson("/api/visual-qa-snapshot-ledger"),
    ledgers: await getJson("/api/visual-qa-snapshot-ledger/ledgers?limit=5"),
  };
  renderVisualQALedger();
}

async function createVisualQALedger() {
  els.visualQALedgerStatus.textContent = "Creating visual QA ledger...";
  const demoPack = state.demoScriptPack && state.demoScriptPack.packs && state.demoScriptPack.packs[0];
  const result = await postJson("/api/visual-qa-snapshot-ledger/create", {
    pack_id: demoPack ? demoPack.pack_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v067 visual QA ledger.",
  });
  state.visualQALedgerCreated = result.ledger || null;
  if (result.error) {
    els.visualQALedgerStatus.textContent = `Visual QA ledger failed: ${result.error}`;
  }
  await loadVisualQALedger();
}

async function loadVisualBaselineComparison() {
  state.visualBaselineComparison = {
    status: await getJson("/api/visual-baseline-comparison"),
    comparisons: await getJson("/api/visual-baseline-comparison/comparisons?limit=5"),
  };
  renderVisualBaselineComparison();
}

async function createVisualBaselineComparison() {
  els.visualBaselineComparisonStatus.textContent = "Creating visual baseline comparison...";
  const ledgers = state.visualQALedger && state.visualQALedger.ledgers ? state.visualQALedger.ledgers : [];
  const result = await postJson("/api/visual-baseline-comparison/create", {
    latest_ledger_id: ledgers[0] ? ledgers[0].ledger_id : "",
    baseline_ledger_id: ledgers[1] ? ledgers[1].ledger_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v067 visual baseline comparison.",
  });
  state.visualBaselineComparisonCreated = result.comparison || null;
  if (result.error) {
    els.visualBaselineComparisonStatus.textContent = `Visual baseline comparison failed: ${result.error}`;
  }
  await loadVisualBaselineComparison();
}

async function loadDemoArtifactCompleteness() {
  state.demoArtifactCompleteness = {
    status: await getJson("/api/demo-artifact-completeness"),
    checks: await getJson("/api/demo-artifact-completeness/checks?limit=5"),
  };
  renderDemoArtifactCompleteness();
}

async function createDemoArtifactCompleteness() {
  els.demoArtifactCompletenessStatus.textContent = "Creating demo artifact completeness check...";
  const result = await postJson("/api/demo-artifact-completeness/create", {
    created_by: "dashboard",
    notes: "Dashboard-created v067 demo artifact completeness check.",
  });
  state.demoArtifactCompletenessCreated = result.check || null;
  if (result.error) {
    els.demoArtifactCompletenessStatus.textContent = `Demo artifact completeness failed: ${result.error}`;
  }
  await loadDemoArtifactCompleteness();
}

async function loadVisualEvidenceCapture() {
  state.visualEvidenceCapture = {
    status: await getJson("/api/visual-evidence-capture"),
    captures: await getJson("/api/visual-evidence-capture/captures?limit=5"),
  };
  renderVisualEvidenceCapture();
}

async function createVisualEvidenceCapture() {
  els.visualEvidenceCaptureStatus.textContent = "Capturing visual evidence screenshots...";
  const ledger = state.visualQALedger && state.visualQALedger.ledgers && state.visualQALedger.ledgers[0];
  const result = await postJson("/api/visual-evidence-capture/create", {
    ledger_id: ledger ? ledger.ledger_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v068 visual evidence capture.",
  });
  state.visualEvidenceCaptureCreated = result.capture || null;
  if (result.error) {
    els.visualEvidenceCaptureStatus.textContent = `Visual evidence capture failed: ${result.error}`;
  }
  await loadVisualEvidenceCapture();
}

async function loadVisualEvidenceReviewDiff() {
  state.visualEvidenceReviewDiff = {
    status: await getJson("/api/visual-evidence-review-diff"),
    diffs: await getJson("/api/visual-evidence-review-diff/diffs?limit=5"),
  };
  renderVisualEvidenceReviewDiff();
}

async function createVisualEvidenceReviewDiff() {
  els.visualEvidenceReviewDiffStatus.textContent = "Creating visual evidence review diff...";
  const capture = state.visualEvidenceCapture && state.visualEvidenceCapture.captures && state.visualEvidenceCapture.captures[0];
  const result = await postJson("/api/visual-evidence-review-diff/create", {
    latest_capture_id: capture ? capture.capture_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v068 visual evidence review diff.",
  });
  state.visualEvidenceReviewDiffCreated = result.diff || null;
  if (result.error) {
    els.visualEvidenceReviewDiffStatus.textContent = `Visual evidence review diff failed: ${result.error}`;
  }
  await loadVisualEvidenceReviewDiff();
}

async function loadVisualEvidenceReviewAnnotations() {
  state.visualEvidenceReviewAnnotations = {
    status: await getJson("/api/visual-evidence-review-annotations"),
    annotations: await getJson("/api/visual-evidence-review-annotations/annotations?limit=5"),
  };
  renderVisualEvidenceReviewAnnotations();
}

async function createVisualEvidenceReviewAnnotations() {
  els.visualEvidenceReviewAnnotationsStatus.textContent = "Creating visual evidence review annotations...";
  const diff = state.visualEvidenceReviewDiff && state.visualEvidenceReviewDiff.diffs && state.visualEvidenceReviewDiff.diffs[0];
  const result = await postJson("/api/visual-evidence-review-annotations/create", {
    diff_id: diff ? diff.diff_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v068 visual evidence review annotations.",
  });
  state.visualEvidenceReviewAnnotationsCreated = result.annotations || null;
  if (result.error) {
    els.visualEvidenceReviewAnnotationsStatus.textContent = `Visual evidence review annotations failed: ${result.error}`;
  }
  await loadVisualEvidenceReviewAnnotations();
}


async function loadVisualEvidenceSignoffPacket() {
  state.visualEvidenceSignoffPacket = {
    status: await getJson("/api/visual-evidence-signoff-packet"),
    packets: await getJson("/api/visual-evidence-signoff-packet/packets?limit=5"),
  };
  renderVisualEvidenceSignoffPacket();
}

async function createVisualEvidenceSignoffPacket() {
  els.visualEvidenceSignoffPacketStatus.textContent = "Creating visual evidence sign-off packet...";
  const annotation = state.visualEvidenceReviewAnnotations && state.visualEvidenceReviewAnnotations.annotations && state.visualEvidenceReviewAnnotations.annotations[0];
  const result = await postJson("/api/visual-evidence-signoff-packet/create", {
    annotation_id: annotation ? annotation.annotation_id : "",
    created_by: "dashboard",
    notes: "Dashboard-created v083 visual evidence sign-off packet.",
  });
  state.visualEvidenceSignoffPacketCreated = result.packet || null;
  if (result.error) {
    els.visualEvidenceSignoffPacketStatus.textContent = `Visual evidence sign-off packet failed: ${result.error}`;
  }
  await loadVisualEvidenceSignoffPacket();
}


async function loadFinalReviewerLaunchChecklist() {
  state.finalReviewerLaunchChecklist = {
    status: await getJson("/api/final-reviewer-launch-checklist"),
    checklists: await getJson("/api/final-reviewer-launch-checklist/checklists?limit=5"),
  };
  renderFinalReviewerLaunchChecklist();
}

async function createFinalReviewerLaunchChecklist() {
  els.finalReviewerLaunchChecklistStatus.textContent = "Creating final reviewer launch checklist...";
  const packet = state.visualEvidenceSignoffPacket && state.visualEvidenceSignoffPacket.packets && state.visualEvidenceSignoffPacket.packets[0];
  const result = await postJson("/api/final-reviewer-launch-checklist/create", {
    packet_id: packet ? packet.packet_id : "",
    created_by: "dashboard",
    reviewer: "dashboard",
    notes: "Dashboard-created v083 final reviewer launch checklist.",
  });
  state.finalReviewerLaunchChecklistCreated = result.checklist || null;
  if (result.error) {
    els.finalReviewerLaunchChecklistStatus.textContent = `Final reviewer launch checklist failed: ${result.error}`;
  }
  await loadFinalReviewerLaunchChecklist();
}

async function loadRecruiterDemoBrief() {
  state.recruiterDemoBrief = {
    status: await getJson("/api/recruiter-demo-brief"),
    briefs: await getJson("/api/recruiter-demo-brief/briefs?limit=5"),
  };
  renderRecruiterDemoBrief();
}

async function createRecruiterDemoBrief() {
  els.recruiterDemoBriefStatus.textContent = "Creating recruiter-facing demo brief...";
  const checklist = state.finalReviewerLaunchChecklist && state.finalReviewerLaunchChecklist.checklists && state.finalReviewerLaunchChecklist.checklists[0];
  const result = await postJson("/api/recruiter-demo-brief/create", {
    checklist_id: checklist ? checklist.checklist_id : "",
    created_by: "dashboard",
    audience: "technical_recruiter",
    notes: "Dashboard-created v083 recruiter-facing demo brief.",
  });
  state.recruiterDemoBriefCreated = result.brief || null;
  if (result.error) {
    els.recruiterDemoBriefStatus.textContent = `Recruiter-facing demo brief failed: ${result.error}`;
  }
  await loadRecruiterDemoBrief();
}

async function loadPublicPortfolioPackage() {
  state.publicPortfolioPackage = {
    status: await getJson("/api/public-portfolio-package"),
    packages: await getJson("/api/public-portfolio-package/packages?limit=5"),
  };
  renderPublicPortfolioPackage();
}

async function createPublicPortfolioPackage() {
  els.publicPortfolioPackageStatus.textContent = "Creating public portfolio package...";
  const brief = state.recruiterDemoBrief && state.recruiterDemoBrief.briefs && state.recruiterDemoBrief.briefs[0];
  const result = await postJson("/api/public-portfolio-package/create", {
    brief_id: brief ? brief.brief_id : "",
    created_by: "dashboard",
    audience: "portfolio_reviewer",
    notes: "Dashboard-created v083 public portfolio interview package.",
  });
  state.publicPortfolioPackageCreated = result.package || null;
  if (result.error) {
    els.publicPortfolioPackageStatus.textContent = `Public portfolio package failed: ${result.error}`;
  }
  await loadPublicPortfolioPackage();
}

async function loadDemoReviewPlaybook() {
  state.demoReviewPlaybook = {
    status: await getJson("/api/demo-review-playbook"),
    playbooks: await getJson("/api/demo-review-playbook/playbooks?limit=5"),
  };
  renderDemoReviewPlaybook();
}

async function createDemoReviewPlaybook() {
  els.demoReviewPlaybookStatus.textContent = "Creating demo review playbook...";
  const pkg = state.publicPortfolioPackage && state.publicPortfolioPackage.packages && state.publicPortfolioPackage.packages[0];
  const result = await postJson("/api/demo-review-playbook/create", {
    package_id: pkg ? pkg.package_id : "",
    created_by: "dashboard",
    audience: "portfolio_reviewer",
    notes: "Dashboard-created v083 demo review playbook.",
  });
  state.demoReviewPlaybookCreated = result.playbook || null;
  if (result.error) {
    els.demoReviewPlaybookStatus.textContent = `Demo review playbook failed: ${result.error}`;
  }
  await loadDemoReviewPlaybook();
}

async function loadGithubPublicationBundle() {
  state.githubPublicationBundle = {
    status: await getJson("/api/github-publication-bundle"),
    bundles: await getJson("/api/github-publication-bundle/bundles?limit=5"),
  };
  renderGithubPublicationBundle();
}

async function createGithubPublicationBundle() {
  els.githubPublicationBundleStatus.textContent = "Creating GitHub publication bundle...";
  const playbook = state.demoReviewPlaybook && state.demoReviewPlaybook.playbooks && state.demoReviewPlaybook.playbooks[0];
  const result = await postJson("/api/github-publication-bundle/create", {
    playbook_id: playbook ? playbook.playbook_id : "",
    created_by: "dashboard",
    audience: "github_portfolio_reviewer",
    notes: "Dashboard-created v083 GitHub-ready publication bundle.",
  });
  state.githubPublicationBundleCreated = result.bundle || null;
  if (result.error) {
    els.githubPublicationBundleStatus.textContent = `GitHub publication bundle failed: ${result.error}`;
  }
  await loadGithubPublicationBundle();
}

async function loadRepositoryPublicationQa() {
  state.repositoryPublicationQa = {
    status: await getJson("/api/repository-publication-qa"),
    reviews: await getJson("/api/repository-publication-qa/reviews?limit=5"),
  };
  renderRepositoryPublicationQa();
}

async function createRepositoryPublicationQa() {
  els.repositoryPublicationQaStatus.textContent = "Creating repository publication QA...";
  const bundle = state.githubPublicationBundle && state.githubPublicationBundle.bundles && state.githubPublicationBundle.bundles[0];
  const result = await postJson("/api/repository-publication-qa/create", {
    bundle_id: bundle ? bundle.bundle_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 repository publication QA.",
  });
  state.repositoryPublicationQaCreated = result.review || null;
  if (result.error) {
    els.repositoryPublicationQaStatus.textContent = `Repository publication QA failed: ${result.error}`;
  }
  await loadRepositoryPublicationQa();
}

async function loadRepositoryExportHandoff() {
  state.repositoryExportHandoff = {
    status: await getJson("/api/repository-export-handoff"),
    handoffs: await getJson("/api/repository-export-handoff/handoffs?limit=5"),
  };
  renderRepositoryExportHandoff();
}

async function createRepositoryExportHandoff() {
  els.repositoryExportHandoffStatus.textContent = "Creating repository export handoff...";
  const review = state.repositoryPublicationQa && state.repositoryPublicationQa.reviews && state.repositoryPublicationQa.reviews[0];
  const result = await postJson("/api/repository-export-handoff/create", {
    repository_qa_id: review ? review.review_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 repository export handoff.",
  });
  state.repositoryExportHandoffCreated = result.handoff || null;
  if (result.error) {
    els.repositoryExportHandoffStatus.textContent = `Repository export handoff failed: ${result.error}`;
  }
  await loadRepositoryExportHandoff();
}

async function loadRepositoryDryRunReview() {
  state.repositoryDryRunReview = {
    status: await getJson("/api/repository-dry-run-review"),
    reviews: await getJson("/api/repository-dry-run-review/reviews?limit=5"),
  };
  renderRepositoryDryRunReview();
}

async function createRepositoryDryRunReview() {
  els.repositoryDryRunReviewStatus.textContent = "Creating repository dry-run review...";
  const handoff = state.repositoryExportHandoff && state.repositoryExportHandoff.handoffs && state.repositoryExportHandoff.handoffs[0];
  const result = await postJson("/api/repository-dry-run-review/create", {
    handoff_id: handoff ? handoff.handoff_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 repository dry-run review.",
  });
  state.repositoryDryRunReviewCreated = result.review || null;
  if (result.error) {
    els.repositoryDryRunReviewStatus.textContent = `Repository dry-run review failed: ${result.error}`;
  }
  await loadRepositoryDryRunReview();
}

async function loadRepositoryFinalPackageReview() {
  state.repositoryFinalPackageReview = {
    status: await getJson("/api/repository-final-package-review"),
    reviews: await getJson("/api/repository-final-package-review/reviews?limit=5"),
  };
  renderRepositoryFinalPackageReview();
}

async function createRepositoryFinalPackageReview() {
  els.repositoryFinalPackageReviewStatus.textContent = "Creating repository final package review...";
  const review = state.repositoryDryRunReview && state.repositoryDryRunReview.reviews && state.repositoryDryRunReview.reviews[0];
  const result = await postJson("/api/repository-final-package-review/create", {
    dry_run_review_id: review ? review.review_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 repository final package review.",
  });
  state.repositoryFinalPackageReviewCreated = result.review || null;
  if (result.error) {
    els.repositoryFinalPackageReviewStatus.textContent = `Repository final package review failed: ${result.error}`;
  }
  await loadRepositoryFinalPackageReview();
}

async function loadPublicReadmeCleanupReview() {
  state.publicReadmeCleanupReview = {
    status: await getJson("/api/public-readme-cleanup-review"),
    reviews: await getJson("/api/public-readme-cleanup-review/reviews?limit=5"),
  };
  renderPublicReadmeCleanupReview();
}

async function createPublicReadmeCleanupReview() {
  els.publicReadmeCleanupReviewStatus.textContent = "Creating public README cleanup review...";
  const review = state.repositoryFinalPackageReview && state.repositoryFinalPackageReview.reviews && state.repositoryFinalPackageReview.reviews[0];
  const result = await postJson("/api/public-readme-cleanup-review/create", {
    final_package_review_id: review ? review.review_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 public README cleanup review.",
  });
  state.publicReadmeCleanupReviewCreated = result.review || null;
  if (result.error) {
    els.publicReadmeCleanupReviewStatus.textContent = `Public README cleanup review failed: ${result.error}`;
  }
  await loadPublicReadmeCleanupReview();
}

async function loadPublicRepositoryPolishPackage() {
  state.publicRepositoryPolishPackage = {
    status: await getJson("/api/public-repository-polish-package"),
    packages: await getJson("/api/public-repository-polish-package/packages?limit=5"),
  };
  renderPublicRepositoryPolishPackage();
}

async function createPublicRepositoryPolishPackage() {
  els.publicRepositoryPolishPackageStatus.textContent = "Creating public repository polish package...";
  const review = state.publicReadmeCleanupReview && state.publicReadmeCleanupReview.reviews && state.publicReadmeCleanupReview.reviews[0];
  const result = await postJson("/api/public-repository-polish-package/create", {
    cleanup_review_id: review ? review.review_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 public repository polish package.",
  });
  state.publicRepositoryPolishPackageCreated = result.package || null;
  if (result.error) {
    els.publicRepositoryPolishPackageStatus.textContent = `Public repository polish package failed: ${result.error}`;
  }
  await loadPublicRepositoryPolishPackage();
}

async function loadRepositoryExportChecklist() {
  state.repositoryExportChecklist = {
    status: await getJson("/api/repository-export-checklist"),
    checklists: await getJson("/api/repository-export-checklist/checklists?limit=5"),
  };
  renderRepositoryExportChecklist();
}

async function createRepositoryExportChecklist() {
  els.repositoryExportChecklistStatus.textContent = "Creating repository export checklist...";
  const pkg = state.publicRepositoryPolishPackage && state.publicRepositoryPolishPackage.packages && state.publicRepositoryPolishPackage.packages[0];
  const result = await postJson("/api/repository-export-checklist/create", {
    package_id: pkg ? pkg.package_id : "",
    created_by: "dashboard",
    audience: "github_repository_reviewer",
    notes: "Dashboard-created v083 UX repair.",
  });
  state.repositoryExportChecklistCreated = result.checklist || null;
  if (result.error) {
    els.repositoryExportChecklistStatus.textContent = `Repository export checklist failed: ${result.error}`;
  }
  await loadRepositoryExportChecklist();
}

async function loadWorkspaceRegistry() {
  state.workspaces = await getJson("/api/workspace-registry");
  populateDashboardWorkspaceSelect();
  renderWorkspaceRegistry();
}

async function loadJobs() {
  state.jobs = await getJson("/api/jobs?limit=8");
  renderJobs();
}

async function loadAnalysisRuns() {
  state.analysisRuns = await getJson("/api/analysis-runs?limit=8");
  renderAnalysisRuns();
}

async function loadPortfolioReports() {
  state.portfolioReports = await getJson("/api/portfolio-reports?limit=8");
  state.exportBundles = await getJson("/api/export-bundles?limit=4");
  renderPortfolioReports();
}

async function loadAnalysisProfiles() {
  const params = new URLSearchParams();
  if (els.sourceSelect.value) params.set("dataset_id", els.sourceSelect.value);
  const pilot = selectedPilot();
  if (pilot) params.set("pilot_osm_id", pilot.osm_id);
  params.set("route_aware", els.pilotRouteAware.checked ? "true" : "false");
  state.analysisProfiles = await getJson(`/api/analysis-profiles?${params.toString()}`);
  renderAnalysisProfiles();
}

async function loadProfileWorkspaces() {
  state.profileWorkspaces = await getJson("/api/profile-workspaces");
  renderProfileWorkspaces();
}

async function loadProductArchitecture() {
  state.productArchitecture = await getJson("/api/product-architecture");
  renderProductArchitecture();
}

async function loadProfileDashboard() {
  state.profileDashboard = await getJson("/api/profile-dashboard");
  renderProfileDashboardOptions();
  await loadProfileDashboardResults();
}

async function loadProfileDashboardResults() {
  const profileId = els.profileDashboardSelect.value || "safe_access_pedestrian_review";
  state.profileDashboardSummary = await getJson(`/api/profile-dashboard/${profileId}/summary`);
  const params = new URLSearchParams();
  params.set("limit", "80");
  state.profileDashboardResults = await getJson(`/api/profile-dashboard/${profileId}/results?${params.toString()}`);
  renderProfileDashboard();
  await loadScoringRules();
}

async function loadScoringRules() {
  const profileId = els.profileDashboardSelect.value || "safe_access_pedestrian_review";
  state.scoringRules = await getJson("/api/scoring-rules");
  state.scoringAudit = await getJson(`/api/scoring-rules/${encodeURIComponent(profileId)}/audit?limit=8`);
  renderScoringRules();
}

async function loadPostgisBackend() {
  state.postgisBackend = {
    status: await getJson("/api/postgis-backend"),
    schema: await getJson("/api/postgis-backend/schema"),
    plan: await getJson("/api/postgis-backend/migration-plan"),
    plans: await getJson("/api/postgis-backend/plans?limit=3"),
  };
  renderPostgisBackend();
}

async function createPostgisPlan() {
  els.postgisBackendStatus.textContent = "Creating PostGIS migration plan...";
  state.postgisPlan = await postJson("/api/postgis-backend/migration-plan", { scope: "kfar_saba_pilot" });
  await loadPostgisBackend();
}

async function loadProfileMapper() {
  state.profileMapper = {
    overview: await getJson("/api/profile-mapper"),
    contracts: await getJson("/api/profile-mapper/contracts"),
    compatibility: await getJson("/api/profile-mapper/compatibility"),
    plan: await getJson("/api/profile-mapper/plan"),
    plans: await getJson("/api/profile-mapper/plans?limit=3"),
  };
  renderProfileMapper();
}

async function createProfileMapperPlan() {
  els.profileMapperStatus.textContent = "Creating profile mapper plan...";
  state.profileMapperPlan = await postJson("/api/profile-mapper/plan", {
    profile_id: "safe_access_pedestrian_review",
    dataset_id: "israel-and-palestine-260521-free-shp-zip",
  });
  await loadProfileMapper();
}

async function loadContractExecution() {
  state.contractExecution = {
    status: await getJson("/api/contract-execution"),
    adapters: await getJson("/api/contract-execution/adapters"),
    dryRun: await getJson("/api/contract-execution/dry-run?profile_id=safe_access_pedestrian_review"),
    dryRuns: await getJson("/api/contract-execution/dry-runs?limit=3"),
  };
  renderContractExecution();
}

async function createContractDryRun() {
  els.contractExecutionStatus.textContent = "Creating contract execution dry run...";
  state.contractDryRun = await postJson("/api/contract-execution/dry-run", {
    profile_id: "safe_access_pedestrian_review",
    dataset_id: "israel-and-palestine-260521-free-shp-zip",
    pilot_osm_id: "53796999",
  });
  await loadContractExecution();
}

function renderOsmTagQuality() {
  const payload = state.osmTagQuality;
  if (!payload || !payload.status || !payload.summary) {
    els.osmTagQualityStatus.textContent = "No OSM tag quality data loaded.";
    els.osmTagQualityBody.innerHTML = "";
    return;
  }
  const counts = payload.summary.counts || {};
  const run = state.osmTagQualityRun;
  els.osmTagQualityStatus.textContent = `${counts.tag_count_rows || 0} audit rows; ${counts.key_evidence_rows || 0} key evidence rows`;
  els.osmTagQualityBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(payload.status.osm_tag_quality_version || "")}</h3>
      <p><b>Sources:</b> ${counts.source_count || 0}; <b>Scopes:</b> ${counts.scope_count || 0}</p>
      <p><b>PBF tag presence rows:</b> ${counts.pbf_presence_rows || 0}; <b>Shapefile gaps:</b> ${counts.shapefile_not_preserved_count || 0}</p>
      <p><b>Workspace:</b> ${escapeHtml(run && run.workspace ? run.workspace.manifest.workspace_id : DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID)}</p>
      <a href="/api/profile-workspaces/${encodeURIComponent(DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID)}/download/tag_quality_summary">Download tag quality CSV</a>
    </div>
  `;
}

async function loadOsmTagQuality() {
  state.osmTagQuality = {
    status: await getJson("/api/osm-tag-quality"),
    summary: await getJson("/api/osm-tag-quality/summary"),
    results: await getJson("/api/osm-tag-quality/results?limit=5"),
  };
  renderOsmTagQuality();
}

async function runOsmTagQuality() {
  els.osmTagQualityStatus.textContent = "Running OSM tag quality profile...";
  state.osmTagQualityRun = await postJson("/api/profile-runners/osm_tag_quality/run", {
    workspace_id: DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID,
  });
  if (!state.osmTagQualityRun.ok) {
    els.osmTagQualityStatus.textContent = `OSM tag quality failed: ${state.osmTagQualityRun.error || "unknown error"}`;
    return;
  }
  await loadOsmTagQuality();
  await loadProfileWorkspaces();
  await loadAnalysisProfiles();
}

function renderTemplateAuthoring() {
  const payload = state.templateAuthoring;
  if (!payload || !payload.status || !payload.options) {
    els.templateAuthoringStatus.textContent = "No template authoring data loaded.";
    els.templateAuthoringBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const blueprints = payload.options.blueprints || [];
  const draft = state.templateDraft;
  els.templateAuthoringStatus.textContent = `${status.blueprint_count || 0} blueprints; ${status.draft_count || 0} drafts`;
  els.templateAuthoringBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.template_authoring_version || "")}</h3>
      <p><b>Existing contracts:</b> ${status.existing_contract_count || 0}; <b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Draft:</b> ${escapeHtml(draft ? draft.draft_id || "" : "none")}</p>
      <p><b>Blueprints:</b> ${blueprints.map((item) => escapeHtml(item.profile_id)).join(", ")}</p>
    </div>
  `;
}

async function loadTemplateAuthoring() {
  state.templateAuthoring = {
    status: await getJson("/api/template-authoring"),
    options: await getJson("/api/template-authoring/options"),
    drafts: await getJson("/api/template-authoring/drafts?limit=3"),
  };
  renderTemplateAuthoring();
}

async function createTemplateDraft() {
  els.templateAuthoringStatus.textContent = "Creating template draft...";
  state.templateDraft = await postJson("/api/template-authoring/draft", {
    template_id: "cycling_micromobility_access",
    dataset_id: "israel-and-palestine-260521-free-shp-zip",
  });
  await loadTemplateAuthoring();
}

function latestTemplateDraftId() {
  if (state.templateDraft && state.templateDraft.draft_id) return state.templateDraft.draft_id;
  const drafts = state.templateAuthoring && state.templateAuthoring.drafts;
  if (Array.isArray(drafts) && drafts.length > 0) return drafts[0].draft_id || "";
  return "";
}

async function ensureTemplateDraftForAuthoredRunner() {
  let draftId = latestTemplateDraftId();
  if (draftId) return draftId;
  await createTemplateDraft();
  return latestTemplateDraftId();
}

function renderAuthoredProfileRunner() {
  const payload = state.authoredProfileRunner;
  if (!payload || !payload.status) {
    els.authoredProfileRunnerStatus.textContent = "No authored runner data loaded.";
    els.authoredProfileRunnerBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const run = state.authoredProfileRun;
  const queueJob = state.authoredQueueJob;
  els.authoredProfileRunnerStatus.textContent = `${status.workspace_count || 0} authored workspaces; ${status.draft_count || 0} drafts`;
  els.authoredProfileRunnerBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.authored_profile_runner_version || "")}</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Latest run:</b> ${escapeHtml(run && run.workspace ? run.workspace.manifest.workspace_id || "" : "none")}</p>
      <p><b>Queued draft job:</b> ${escapeHtml(queueJob ? queueJob.job_id || "" : "none")}</p>
      <p><b>Queue status:</b> ${escapeHtml(queueJob ? queueJob.status || "" : "")}</p>
    </div>
  `;
}

async function loadAuthoredProfileRunner() {
  state.authoredProfileRunner = {
    status: await getJson("/api/authored-profile-runner"),
    workspaces: await getJson("/api/authored-profile-runner/workspaces"),
  };
  renderAuthoredProfileRunner();
}

async function runAuthoredProfile() {
  els.authoredProfileRunnerStatus.textContent = "Running latest authored draft...";
  const draftId = await ensureTemplateDraftForAuthoredRunner();
  state.authoredProfileRun = await postJson("/api/authored-profile-runner/run", {
    draft_id: draftId,
    workspace_id: DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID,
  });
  await loadAuthoredProfileRunner();
  await loadProfileWorkspaces();
  await loadProfileDashboard();
}

async function enqueueAuthoredDraft() {
  els.authoredProfileRunnerStatus.textContent = "Queueing latest authored draft...";
  const draftId = await ensureTemplateDraftForAuthoredRunner();
  state.authoredQueueJob = await postJson("/api/execution-queue/enqueue-authored-draft", {
    draft_id: draftId,
    workspace_id: DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID,
    execute_now: true,
  });
  await loadAuthoredProfileRunner();
  await loadExecutionQueue();
  await loadProfileWorkspaces();
  await loadProfileDashboard();
}

function renderProfilePromotion() {
  const payload = state.profilePromotion;
  if (!payload || !payload.status) {
    els.profilePromotionStatus.textContent = "No promotion data loaded.";
    els.profilePromotionBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const candidates = payload.candidates || [];
  const proposals = payload.proposals || [];
  const queue = payload.reviewQueue || [];
  const latest = state.profilePromotionProposal && state.profilePromotionProposal.proposal ? state.profilePromotionProposal.proposal : null;
  const decision = state.profileAcceptanceDecision && state.profileAcceptanceDecision.decision ? state.profileAcceptanceDecision.decision : null;
  const contractDiff = state.profileContractDiff && state.profileContractDiff.contract_diff ? state.profileContractDiff.contract_diff : null;
  const applicationPlan = state.profileApplicationPlan && state.profileApplicationPlan.application_plan ? state.profileApplicationPlan.application_plan : null;
  const configApplyProposal = state.profileConfigApplyProposal && state.profileConfigApplyProposal.config_apply_proposal ? state.profileConfigApplyProposal.config_apply_proposal : null;
  const regressionPreview = state.profileRegressionPreview && state.profileRegressionPreview.regression_preview ? state.profileRegressionPreview.regression_preview : null;
  const firstCandidate = candidates[0] || {};
  const firstQueue = queue[0] || {};
  const diffCandidates = payload.diffCandidates || [];
  const contractDiffs = payload.contractDiffs || [];
  const applicationCandidates = payload.applicationCandidates || [];
  const applicationPlans = payload.applicationPlans || [];
  const applyCandidates = payload.applyCandidates || [];
  const applyProposals = payload.applyProposals || [];
  const regressionCandidates = payload.regressionCandidates || [];
  const regressionPreviews = payload.regressionPreviews || [];
  els.profilePromotionStatus.textContent = `${status.promotable_candidate_count || 0} promotable candidates; ${status.pending_review_count || 0} pending reviews; ${status.contract_diff_count || 0} contract diffs; ${status.application_plan_count || 0} application plans; ${status.config_apply_proposal_count || 0} apply proposals; ${status.regression_preview_count || 0} regression previews`;
  els.profilePromotionBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.profile_promotion_version || "")}</h3>
      <p><b>Acceptance:</b> ${escapeHtml(status.profile_acceptance_version || "")}</p>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Candidate:</b> ${escapeHtml(firstCandidate.workspace_id || "none")}</p>
      <p><b>Recommendation:</b> ${escapeHtml(firstCandidate.recommendation || "")}</p>
      <p><b>Review queue:</b> ${escapeHtml(firstQueue.proposal_id || "none")} (${escapeHtml(firstQueue.decision_status || "pending_review")})</p>
      <p><b>Latest proposal:</b> ${escapeHtml(latest ? latest.proposal_id || "" : (proposals[0] ? proposals[0].proposal_id || "" : "none"))}</p>
      <p><b>Latest decision:</b> ${escapeHtml(decision ? `${decision.decision_status} by ${decision.reviewer}` : "none")}</p>
      <p><b>Diff candidate:</b> ${escapeHtml(diffCandidates[0] ? diffCandidates[0].proposal_id || "" : "none")}</p>
      <p><b>Latest contract diff:</b> ${escapeHtml(contractDiff ? contractDiff.diff_id || "" : (contractDiffs[0] ? contractDiffs[0].diff_id || "" : "none"))}</p>
      <p><b>Diff counts:</b> ${escapeHtml(contractDiff ? `${contractDiff.summary ? contractDiff.summary.changed_count || 0 : 0} changed / ${contractDiff.summary ? contractDiff.summary.added_count || 0 : 0} added` : "none")}</p>
      <p><b>Application candidate:</b> ${escapeHtml(applicationCandidates[0] ? applicationCandidates[0].proposal_id || "" : "none")}</p>
      <p><b>Latest application plan:</b> ${escapeHtml(applicationPlan ? applicationPlan.plan_id || "" : (applicationPlans[0] ? applicationPlans[0].plan_id || "" : "none"))}</p>
      <p><b>Apply candidate:</b> ${escapeHtml(applyCandidates[0] ? applyCandidates[0].application_plan_id || "" : "none")}</p>
      <p><b>Latest apply proposal:</b> ${escapeHtml(configApplyProposal ? configApplyProposal.apply_id || "" : (applyProposals[0] ? applyProposals[0].apply_id || "" : "none"))}</p>
      <p><b>Regression candidate:</b> ${escapeHtml(regressionCandidates[0] ? regressionCandidates[0].apply_id || "" : "none")}</p>
      <p><b>Latest regression preview:</b> ${escapeHtml(regressionPreview ? `${regressionPreview.preview_id || ""} (${regressionPreview.regression_status || ""})` : (regressionPreviews[0] ? regressionPreviews[0].preview_id || "" : "none"))}</p>
      <p><b>Config mutation:</b> no automatic config mutation; separate explicit implementation required.</p>
    </div>
  `;
}

async function loadProfilePromotion() {
  state.profilePromotion = {
    status: await getJson("/api/profile-promotion"),
    candidates: await getJson("/api/profile-promotion/candidates?limit=6"),
    reviewQueue: await getJson("/api/profile-promotion/review-queue?limit=6"),
    proposals: await getJson("/api/profile-promotion/proposals?limit=4"),
    decisions: await getJson("/api/profile-promotion/decisions?limit=4"),
    diffCandidates: await getJson("/api/profile-promotion/diff-candidates?limit=4"),
    contractDiffs: await getJson("/api/profile-promotion/contract-diffs?limit=4"),
    applicationCandidates: await getJson("/api/profile-promotion/application-candidates?limit=4"),
    applicationPlans: await getJson("/api/profile-promotion/application-plans?limit=4"),
    applyCandidates: await getJson("/api/profile-promotion/apply-candidates?limit=4"),
    applyProposals: await getJson("/api/profile-promotion/config-apply-proposals?limit=4"),
    regressionCandidates: await getJson("/api/profile-promotion/regression-candidates?limit=4"),
    regressionPreviews: await getJson("/api/profile-promotion/regression-previews?limit=4"),
  };
  renderProfilePromotion();
}


function renderReleaseReadiness() {
  const payload = state.releaseReadiness;
  if (!payload || !payload.overview) {
    els.releaseReadinessStatus.textContent = "No release readiness data loaded.";
    els.releaseReadinessBody.innerHTML = "";
    return;
  }
  const overview = payload.overview;
  const summary = overview.summary || {};
  const gates = payload.gates && payload.gates.gates ? payload.gates.gates : overview.gates || [];
  const openActions = overview.required_next_actions || [];
  els.releaseReadinessStatus.textContent = `${overview.readiness_level || "unknown"}; ${summary.passed_gate_count || 0}/${summary.gate_count || 0} gates passed; ${summary.failed_gate_count || 0} failed; ${summary.warning_gate_count || 0} warnings`;
  const gateRows = gates.slice(0, 8).map((gate) => `
    <tr>
      <td>${escapeHtml(gate.gate_id || "")}</td>
      <td><span class="pill">${escapeHtml(gate.status || "")}</span></td>
      <td>${escapeHtml(gate.label || "")}</td>
    </tr>
  `).join("");
  const latestSnapshot = state.releaseReadinessSnapshot && state.releaseReadinessSnapshot.snapshot ? state.releaseReadinessSnapshot.snapshot : null;
  els.releaseReadinessBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(overview.release_readiness_version || "")}</h3>
      <p><b>App:</b> ${escapeHtml(overview.app_version || "")}</p>
      <p><b>Manifest:</b> ${escapeHtml(overview.project_manifest_version || "")}</p>
      <p><b>API endpoints:</b> ${escapeHtml(summary.checked_api_endpoints || 0)}</p>
      <p><b>Profile rows:</b> ${escapeHtml(summary.profile_result_rows || 0)}</p>
      <p><b>Latest snapshot:</b> ${escapeHtml(latestSnapshot ? latestSnapshot.snapshot_id || "" : "none")}</p>
      <p><b>Source GIS modified:</b> ${overview.source_gis_modified === false ? "false" : "check required"}</p>
      <table>
        <thead><tr><th>Gate</th><th>Status</th><th>Evidence</th></tr></thead>
        <tbody>${gateRows}</tbody>
      </table>
      <p><b>Next actions:</b> ${openActions.length ? openActions.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("") : "none"}</p>
    </div>
  `;
}

async function loadReleaseReadiness() {
  state.releaseReadiness = {
    overview: await getJson("/api/release-readiness"),
    gates: await getJson("/api/release-readiness/gates"),
    snapshots: await getJson("/api/release-readiness/snapshots?limit=4"),
  };
  renderReleaseReadiness();
}

async function createReleaseReadinessSnapshot() {
  els.releaseReadinessStatus.textContent = "Creating release readiness snapshot...";
  state.releaseReadinessSnapshot = await postJson("/api/release-readiness/snapshot", {
    created_by: "local_dashboard",
    notes: "Snapshot created from the v053 dashboard.",
  });
  await loadReleaseReadiness();
}


function renderPortfolioDemo() {
  const payload = state.portfolioDemo;
  if (!payload || !payload.overview) {
    els.portfolioDemoStatus.textContent = "No portfolio demo data loaded.";
    els.portfolioDemoBody.innerHTML = "";
    return;
  }
  const overview = payload.overview;
  const metrics = overview.demo_metrics || {};
  const steps = payload.steps && payload.steps.steps ? payload.steps.steps : overview.steps || [];
  const latestSnapshot = state.portfolioDemoSnapshot && state.portfolioDemoSnapshot.snapshot ? state.portfolioDemoSnapshot.snapshot : null;
  els.portfolioDemoStatus.textContent = `${overview.step_count || 0} steps; ${metrics.profile_result_rows || 0} profile rows; readiness ${metrics.readiness_level || "unknown"}`;
  const rows = steps.map((step) => `
    <tr>
      <td>${escapeHtml(step.step_id || "")}</td>
      <td>${escapeHtml(step.title || "")}</td>
      <td>${escapeHtml(step.reviewer_takeaway || "")}</td>
    </tr>
  `).join("");
  els.portfolioDemoBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(overview.portfolio_demo_version || "")}</h3>
      <p><b>Title:</b> ${escapeHtml(overview.title || "")}</p>
      <p><b>Duration:</b> ${escapeHtml(overview.estimated_duration_min || 0)} min</p>
      <p><b>Readiness:</b> ${escapeHtml(metrics.readiness_level || "")}</p>
      <p><b>API endpoints:</b> ${escapeHtml(metrics.api_checked_endpoints || 0)}</p>
      <p><b>Latest snapshot:</b> ${escapeHtml(latestSnapshot ? latestSnapshot.snapshot_id || "" : "none")}</p>
      <table>
        <thead><tr><th>Step</th><th>Title</th><th>Reviewer takeaway</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p><b>Claim boundary:</b> ${escapeHtml(overview.claim_boundary || "")}</p>
    </div>
  `;
}

async function loadPortfolioDemo() {
  state.portfolioDemo = {
    overview: await getJson("/api/portfolio-demo"),
    steps: await getJson("/api/portfolio-demo/steps"),
    snapshots: await getJson("/api/portfolio-demo/snapshots?limit=4"),
  };
  renderPortfolioDemo();
}

async function createPortfolioDemoSnapshot() {
  els.portfolioDemoStatus.textContent = "Creating portfolio demo snapshot...";
  state.portfolioDemoSnapshot = await postJson("/api/portfolio-demo/snapshot", {
    created_by: "local_dashboard",
    notes: "Snapshot created from the v053 guided portfolio demo.",
  });
  await loadPortfolioDemo();
}


function renderPortfolioEvidenceBundle() {
  const payload = state.portfolioEvidenceBundle;
  if (!payload || !payload.status) {
    els.portfolioEvidenceBundleStatus.textContent = "No portfolio evidence bundle data loaded.";
    els.portfolioEvidenceBundleBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const bundles = payload.bundles || [];
  const created = state.portfolioEvidenceBundleCreated && state.portfolioEvidenceBundleCreated.bundle ? state.portfolioEvidenceBundleCreated.bundle : null;
  const latest = created || bundles[0] || {};
  els.portfolioEvidenceBundleStatus.textContent = `${status.bundle_count || 0} bundles; latest ${latest.bundle_id || "none"}`;
  const evidence = (status.evidence_sections || []).map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("");
  els.portfolioEvidenceBundleBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.portfolio_evidence_bundle_version || "")}</h3>
      <p><b>App:</b> ${escapeHtml(status.app_version || "")}</p>
      <p><b>Latest bundle:</b> ${escapeHtml(latest.bundle_id || "none")}</p>
      <p><b>Copied files:</b> ${escapeHtml(latest.copied_file_count || 0)}</p>
      <p><b>Bundle dir:</b> ${escapeHtml(status.bundle_dir || "")}</p>
      <p><b>Evidence:</b> ${evidence}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadPortfolioEvidenceBundle() {
  state.portfolioEvidenceBundle = {
    status: await getJson("/api/portfolio-evidence-bundle"),
    bundles: await getJson("/api/portfolio-evidence-bundle/bundles?limit=4"),
  };
  renderPortfolioEvidenceBundle();
}

async function createPortfolioEvidenceBundle() {
  els.portfolioEvidenceBundleStatus.textContent = "Creating portfolio evidence bundle...";
  state.portfolioEvidenceBundleCreated = await postJson("/api/portfolio-evidence-bundle/create", {
    created_by: "local_dashboard",
    notes: "Snapshot-backed v053 portfolio evidence bundle.",
    reuse_latest: true,
  });
  await loadPortfolioEvidenceBundle();
}


function renderBundleReviewChecklist() {
  const payload = state.bundleReviewChecklist;
  if (!payload || !payload.status) {
    els.bundleReviewChecklistStatus.textContent = "No bundle review checklist data loaded.";
    els.bundleReviewChecklistBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const checklists = payload.checklists || [];
  const created = state.bundleReviewChecklistCreated && state.bundleReviewChecklistCreated.checklist ? state.bundleReviewChecklistCreated.checklist : null;
  const latest = created || checklists[0] || {};
  const summary = created ? created.summary || {} : status.summary || {};
  const readiness = summary.review_readiness || latest.review_readiness || "unknown";
  els.bundleReviewChecklistStatus.textContent = `${summary.check_count || 0} checks; ${summary.failed_count || 0} failed; ${summary.warning_count || 0} warnings; ${readiness}`;
  const checks = created && created.checks ? created.checks : [];
  const rows = checks.slice(0, 8).map((check) => `
    <tr>
      <td>${escapeHtml(check.check_id || "")}</td>
      <td>${escapeHtml(check.status || "")}</td>
      <td>${escapeHtml(check.remediation_action || "")}</td>
    </tr>
  `).join("");
  const steps = (status.guided_review_steps || []).map((step) => `<span class="pill">${escapeHtml(step.step_id || step.label || "")}</span>`).join("");
  els.bundleReviewChecklistBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.bundle_review_checklist_version || "")}</h3>
      <p><b>Latest bundle:</b> ${escapeHtml(status.latest_bundle_id || latest.bundle_id || "none")}</p>
      <p><b>Latest checklist:</b> ${escapeHtml(latest.checklist_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Review steps:</b> ${steps}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
      ${rows ? `<table><thead><tr><th>Check</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
    </div>
  `;
}

async function loadBundleReviewChecklist() {
  state.bundleReviewChecklist = {
    status: await getJson("/api/bundle-review-checklist"),
    checklists: await getJson("/api/bundle-review-checklist/checklists?limit=4"),
  };
  renderBundleReviewChecklist();
}

async function createBundleReviewChecklist() {
  els.bundleReviewChecklistStatus.textContent = "Creating bundle review checklist...";
  state.bundleReviewChecklistCreated = await postJson("/api/bundle-review-checklist/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 bundle review checklist.",
    create_bundle: true,
    reuse_latest: true,
  });
  await loadBundleReviewChecklist();
}


function renderPortfolioNarrative() {
  const payload = state.portfolioNarrative;
  if (!payload || !payload.status) {
    els.portfolioNarrativeStatus.textContent = "No portfolio narrative data loaded.";
    els.portfolioNarrativeBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const narratives = payload.narratives || [];
  const created = state.portfolioNarrativeCreated && state.portfolioNarrativeCreated.narrative ? state.portfolioNarrativeCreated.narrative : null;
  const latest = created || narratives[0] || {};
  const readiness = latest.narrative_readiness || "unknown";
  els.portfolioNarrativeStatus.textContent = `${status.narrative_count || 0} narratives; latest ${latest.narrative_id || "none"}; ${readiness}`;
  const sections = (created && created.sections ? created.sections : (status.narrative_sections || []).map((sectionId) => ({ section_id: sectionId, title: sectionId })));
  const sectionPills = sections.map((section) => `<span class="pill">${escapeHtml(section.section_id || section.title || section)}</span>`).join("");
  const handoff = created && created.reviewer_handoff ? created.reviewer_handoff : {};
  els.portfolioNarrativeBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.portfolio_narrative_export_version || "")}</h3>
      <p><b>Latest checklist:</b> ${escapeHtml(status.latest_checklist_id || latest.checklist_id || "none")}</p>
      <p><b>Latest narrative:</b> ${escapeHtml(latest.narrative_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Sections:</b> ${sectionPills}</p>
      <p><b>Shareable:</b> ${(handoff.shareable_artifacts || []).map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadPortfolioNarrative() {
  state.portfolioNarrative = {
    status: await getJson("/api/portfolio-narrative-export"),
    narratives: await getJson("/api/portfolio-narrative-export/narratives?limit=4"),
  };
  renderPortfolioNarrative();
}

async function createPortfolioNarrative() {
  els.portfolioNarrativeStatus.textContent = "Creating portfolio narrative...";
  state.portfolioNarrativeCreated = await postJson("/api/portfolio-narrative-export/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 portfolio narrative.",
    create_checklist: true,
    create_bundle: true,
    reuse_latest: true,
  });
  await loadPortfolioNarrative();
}


function renderPortfolioHandoff() {
  const payload = state.portfolioHandoff;
  if (!payload || !payload.status) {
    els.portfolioHandoffStatus.textContent = "No portfolio handoff data loaded.";
    els.portfolioHandoffBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const pages = payload.pages || [];
  const created = state.portfolioHandoffCreated && state.portfolioHandoffCreated.page ? state.portfolioHandoffCreated.page : null;
  const latest = created || pages[0] || {};
  const readiness = latest.handoff_readiness || "unknown";
  els.portfolioHandoffStatus.textContent = `${status.page_count || 0} pages; latest ${latest.page_id || "none"}; ${readiness}`;
  const sections = (status.page_sections || []).map((section) => `<span class="pill">${escapeHtml(section)}</span>`).join("");
  const htmlFile = latest.html_file || (latest.files ? latest.files.html : "");
  els.portfolioHandoffBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.portfolio_handoff_page_version || "")}</h3>
      <p><b>Latest narrative:</b> ${escapeHtml(status.latest_narrative_id || latest.narrative_id || "none")}</p>
      <p><b>Latest page:</b> ${escapeHtml(latest.page_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Sections:</b> ${sections}</p>
      <p><b>HTML:</b> ${escapeHtml(htmlFile || "not generated")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadPortfolioHandoff() {
  state.portfolioHandoff = {
    status: await getJson("/api/portfolio-handoff-page"),
    pages: await getJson("/api/portfolio-handoff-page/pages?limit=4"),
  };
  renderPortfolioHandoff();
}

async function createPortfolioHandoff() {
  els.portfolioHandoffStatus.textContent = "Creating portfolio handoff page...";
  state.portfolioHandoffCreated = await postJson("/api/portfolio-handoff-page/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 portfolio handoff page.",
    create_narrative: true,
    create_checklist: true,
    create_bundle: true,
    reuse_latest: true,
  });
  await loadPortfolioHandoff();
}

function renderPortfolioEvidenceGallery() {
  const payload = state.portfolioEvidenceGallery;
  if (!payload || !payload.status) {
    els.portfolioEvidenceGalleryStatus.textContent = "No portfolio gallery data loaded.";
    els.portfolioEvidenceGalleryBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const galleries = payload.galleries || [];
  const created = state.portfolioEvidenceGalleryCreated && state.portfolioEvidenceGalleryCreated.gallery ? state.portfolioEvidenceGalleryCreated.gallery : null;
  const latest = created || galleries[0] || {};
  const counts = latest.artifact_counts || status.artifact_counts || {};
  const readiness = latest.gallery_readiness || "unknown";
  els.portfolioEvidenceGalleryStatus.textContent = `${status.gallery_count || 0} galleries; latest ${latest.gallery_id || "none"}; ${readiness}`;
  const countHtml = Object.entries(counts)
    .map(([key, value]) => `<span class="pill">${escapeHtml(key)}: ${escapeHtml(value)}</span>`)
    .join("");
  const htmlFile = latest.html_file || (latest.files ? latest.files.html : "");
  els.portfolioEvidenceGalleryBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.portfolio_evidence_gallery_version || "")}</h3>
      <p><b>Latest gallery:</b> ${escapeHtml(latest.gallery_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Artifact counts:</b> ${countHtml}</p>
      <p><b>HTML:</b> ${escapeHtml(htmlFile || "not generated")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadPortfolioEvidenceGallery() {
  state.portfolioEvidenceGallery = {
    status: await getJson("/api/portfolio-evidence-gallery"),
    galleries: await getJson("/api/portfolio-evidence-gallery/galleries?limit=4"),
  };
  renderPortfolioEvidenceGallery();
}

async function createPortfolioEvidenceGallery() {
  els.portfolioEvidenceGalleryStatus.textContent = "Creating portfolio evidence gallery...";
  state.portfolioEvidenceGalleryCreated = await postJson("/api/portfolio-evidence-gallery/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 portfolio evidence gallery.",
    create_handoff_page: true,
    create_narrative: true,
    create_checklist: true,
    create_bundle: true,
    reuse_latest: true,
  });
  await loadPortfolioEvidenceGallery();
}



function renderMultiPilotComparison() {
  const payload = state.multiPilotComparison;
  if (!payload || !payload.status) {
    els.multiPilotComparisonStatus.textContent = "No multi-pilot comparison data loaded.";
    els.multiPilotComparisonBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const comparisons = payload.comparisons || [];
  const created = state.multiPilotComparisonCreated && state.multiPilotComparisonCreated.comparison ? state.multiPilotComparisonCreated.comparison : null;
  const latest = created || comparisons[0] || {};
  const readiness = latest.comparison_readiness || status.latest_readiness || "unknown";
  const pilots = status.pilot_statuses || [];
  const pilotHtml = pilots.map((row) => `
    <div class="mini-row">
      <span>${escapeHtml(row.pilot_label || row.route_workspace_id || "")}</span>
      <b>${row.route_workspace_exists ? "ready" : "missing"}</b>
    </div>
  `).join("");
  const matrixRows = (latest.comparison_matrix || []).slice(0, 6).map((row) => {
    const values = Object.entries(row.values || {}).map(([key, value]) => `${key}: ${value}`).join(" | ");
    return `<div class="mini-row"><span>${escapeHtml(row.label || row.metric_id)}</span><b>${escapeHtml(values)}</b></div>`;
  }).join("");
  const htmlFile = latest.html_file || (latest.files ? latest.files.html : "");
  els.multiPilotComparisonStatus.textContent = `${status.ready_pilot_count || 0}/${status.default_pilot_count || 0} pilots ready; ${status.comparison_count || 0} comparisons; ${readiness}`;
  els.multiPilotComparisonBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.multi_pilot_comparison_version || "")}</h3>
      <p><b>Latest comparison:</b> ${escapeHtml(latest.comparison_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Pilot workspaces:</b></p>
      ${pilotHtml || "<p>No pilots configured.</p>"}
      <p><b>Comparison matrix:</b></p>
      ${matrixRows || "<p>No comparison generated yet.</p>"}
      <p><b>HTML:</b> ${escapeHtml(htmlFile || "not generated")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadMultiPilotComparison() {
  state.multiPilotComparison = {
    status: await getJson("/api/multi-pilot-comparison"),
    comparisons: await getJson("/api/multi-pilot-comparison/comparisons?limit=4"),
  };
  renderMultiPilotComparison();
}

async function createMultiPilotComparison() {
  els.multiPilotComparisonStatus.textContent = "Creating multi-pilot comparison...";
  state.multiPilotComparisonCreated = await postJson("/api/multi-pilot-comparison/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 multi-pilot comparison.",
  });
  await loadMultiPilotComparison();
}



function renderComparisonMapExports() {
  const payload = state.comparisonMapExports;
  if (!payload || !payload.status) {
    els.comparisonMapExportsStatus.textContent = "No comparison map export data loaded.";
    els.comparisonMapExportsBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const exports = payload.exports || [];
  const created = state.comparisonMapExportCreated && state.comparisonMapExportCreated.export ? state.comparisonMapExportCreated.export : null;
  const latest = created || exports[0] || {};
  const readiness = latest.export_readiness || status.latest_readiness || "unknown";
  const pilotRows = (status.pilot_statuses || []).map((row) => `
    <div class="mini-row">
      <span>${escapeHtml(row.pilot_label || row.route_workspace_id || "")}</span>
      <b>${row.required_tables_present ? "ready" : "missing tables"}</b>
    </div>
  `).join("");
  const mapRows = (latest.pilot_maps || []).map((row) => `
    <div class="mini-row">
      <span>${escapeHtml(row.pilot_label || "")}</span>
      <b>${escapeHtml(row.top_candidate_count || 0)} top rows</b>
    </div>
  `).join("");
  const htmlFile = latest.html_file || (latest.files ? latest.files.html : "");
  const csvFile = latest.csv_file || (latest.files ? latest.files.top_candidates_csv : "");
  els.comparisonMapExportsStatus.textContent = `${status.ready_pilot_count || 0}/${status.default_pilot_count || 0} pilots ready; ${status.export_count || 0} exports; ${readiness}`;
  els.comparisonMapExportsBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.comparison_map_exports_version || "")}</h3>
      <p><b>Latest export:</b> ${escapeHtml(latest.export_id || "none")}</p>
      <p><b>Readiness:</b> ${escapeHtml(readiness)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Pilot table readiness:</b></p>
      ${pilotRows || "<p>No pilots configured.</p>"}
      <p><b>Generated pilot maps:</b></p>
      ${mapRows || "<p>No map export generated yet.</p>"}
      <p><b>HTML:</b> ${escapeHtml(htmlFile || "not generated")}</p>
      <p><b>CSV:</b> ${escapeHtml(csvFile || "not generated")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
  `;
}

async function loadComparisonMapExports() {
  state.comparisonMapExports = {
    status: await getJson("/api/comparison-map-exports"),
    exports: await getJson("/api/comparison-map-exports/exports?limit=4"),
  };
  renderComparisonMapExports();
}

async function createComparisonMapExport() {
  els.comparisonMapExportsStatus.textContent = "Creating comparison map export...";
  state.comparisonMapExportCreated = await postJson("/api/comparison-map-exports/create", {
    created_by: "local_dashboard",
    notes: "Dashboard-created v053 comparison map export.",
    top_limit: 20,
  });
  await loadComparisonMapExports();
}

async function createProfilePromotionProposal() {
  els.profilePromotionStatus.textContent = "Creating promotion proposal...";
  if (!state.profilePromotion || !state.profilePromotion.candidates || state.profilePromotion.candidates.length === 0) {
    await loadProfilePromotion();
  }
  const candidates = state.profilePromotion && state.profilePromotion.candidates ? state.profilePromotion.candidates : [];
  const candidate = candidates.find((row) => row.recommendation === "ready_for_promotion_proposal") || candidates[0] || {};
  state.profilePromotionProposal = await postJson("/api/profile-promotion/propose", {
    workspace_id: candidate.workspace_id || DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID,
  });
  await loadProfilePromotion();
}

function latestPromotionProposalId() {
  if (state.profilePromotionProposal && state.profilePromotionProposal.proposal) return state.profilePromotionProposal.proposal.proposal_id;
  const queue = state.profilePromotion && state.profilePromotion.reviewQueue ? state.profilePromotion.reviewQueue : [];
  const pending = queue.find((row) => row.decision_status === "pending_review") || queue[0];
  if (pending && pending.proposal_id) return pending.proposal_id;
  const proposals = state.profilePromotion && state.profilePromotion.proposals ? state.profilePromotion.proposals : [];
  return proposals[0] ? proposals[0].proposal_id || "" : "";
}

async function recordProfilePromotionDecision(decision) {
  if (!state.profilePromotion || !state.profilePromotion.proposals || state.profilePromotion.proposals.length === 0) {
    await loadProfilePromotion();
  }
  let proposalId = latestPromotionProposalId();
  if (!proposalId) {
    await createProfilePromotionProposal();
    proposalId = latestPromotionProposalId();
  }
  els.profilePromotionStatus.textContent = `Recording ${decision} decision...`;
  state.profileAcceptanceDecision = await postJson(`/api/profile-promotion/proposals/${encodeURIComponent(proposalId)}/decision`, {
    decision,
    reviewer: "local_reviewer",
    notes: decision === "approve" ? "Approved for later manual implementation review." : "Rejected in local review workflow.",
  });
  await loadProfilePromotion();
}

async function createProfileContractDiff() {
  if (!state.profilePromotion || !state.profilePromotion.diffCandidates || state.profilePromotion.diffCandidates.length === 0) {
    await loadProfilePromotion();
  }
  let candidates = state.profilePromotion && state.profilePromotion.diffCandidates ? state.profilePromotion.diffCandidates : [];
  let candidate = candidates.find((row) => row.diff_status === "ready_for_contract_diff") || candidates[0];
  if (!candidate) {
    await createProfilePromotionProposal();
    await loadProfilePromotion();
    candidates = state.profilePromotion && state.profilePromotion.diffCandidates ? state.profilePromotion.diffCandidates : [];
    candidate = candidates[0];
  }
  els.profilePromotionStatus.textContent = "Creating contract diff review...";
  state.profileContractDiff = await postJson("/api/profile-promotion/contract-diff", {
    proposal_id: candidate ? candidate.proposal_id || "" : "",
  });
  await loadProfilePromotion();
}

async function createProfileApplicationPlan() {
  if (!state.profilePromotion || !state.profilePromotion.applicationCandidates || state.profilePromotion.applicationCandidates.length === 0) {
    await loadProfilePromotion();
  }
  const candidates = state.profilePromotion && state.profilePromotion.applicationCandidates ? state.profilePromotion.applicationCandidates : [];
  let candidate = candidates.find((row) => row.application_status === "ready_for_application_plan") || candidates[0];
  if (!candidate) {
    await recordProfilePromotionDecision("approve");
    await loadProfilePromotion();
    candidate = state.profilePromotion.applicationCandidates[0];
  }
  els.profilePromotionStatus.textContent = "Creating application plan...";
  state.profileApplicationPlan = await postJson("/api/profile-promotion/application-plan", {
    proposal_id: candidate ? candidate.proposal_id || "" : "",
    decision_id: candidate ? candidate.decision_id || "" : "",
  });
  await loadProfilePromotion();
}

async function createProfileConfigApplyProposal() {
  if (!state.profilePromotion || !state.profilePromotion.applyCandidates || state.profilePromotion.applyCandidates.length === 0) {
    await loadProfilePromotion();
  }
  let candidates = state.profilePromotion && state.profilePromotion.applyCandidates ? state.profilePromotion.applyCandidates : [];
  let candidate = candidates.find((row) => row.apply_status === "ready_for_apply_proposal") || candidates[0];
  if (!candidate) {
    await createProfileApplicationPlan();
    await loadProfilePromotion();
    candidates = state.profilePromotion && state.profilePromotion.applyCandidates ? state.profilePromotion.applyCandidates : [];
    candidate = candidates[0];
  }
  els.profilePromotionStatus.textContent = "Creating guarded apply proposal...";
  state.profileConfigApplyProposal = await postJson("/api/profile-promotion/config-apply-proposal", {
    application_plan_id: candidate ? candidate.application_plan_id || "" : "",
    proposal_id: candidate ? candidate.proposal_id || "" : "",
  });
  await loadProfilePromotion();
}

async function createProfileRegressionPreview() {
  if (!state.profilePromotion || !state.profilePromotion.regressionCandidates || state.profilePromotion.regressionCandidates.length === 0) {
    await loadProfilePromotion();
  }
  let candidates = state.profilePromotion && state.profilePromotion.regressionCandidates ? state.profilePromotion.regressionCandidates : [];
  let candidate = candidates.find((row) => row.regression_status === "ready_for_regression_preview") || candidates[0];
  if (!candidate) {
    await createProfileConfigApplyProposal();
    await loadProfilePromotion();
    candidates = state.profilePromotion && state.profilePromotion.regressionCandidates ? state.profilePromotion.regressionCandidates : [];
    candidate = candidates[0];
  }
  els.profilePromotionStatus.textContent = "Creating regression preview...";
  state.profileRegressionPreview = await postJson("/api/profile-promotion/regression-preview", {
    apply_id: candidate ? candidate.apply_id || "" : "",
    proposal_id: candidate ? candidate.proposal_id || "" : "",
  });
  await loadProfilePromotion();
}

function renderExecutionQueue() {
  const payload = state.executionQueue;
  if (!payload || !payload.status) {
    els.executionQueueStatus.textContent = "No execution queue data loaded.";
    els.executionQueueBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const job = state.executionQueueJob;
  els.executionQueueStatus.textContent = `${status.executable_profile_count || 0} executable profiles; ${status.job_count || 0} jobs`;
  els.executionQueueBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.execution_queue_version || "")}</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Latest job:</b> ${escapeHtml(job ? job.job_id || "" : "none")}</p>
      <p><b>Status:</b> ${escapeHtml(job ? job.status || "" : "")}</p>
    </div>
  `;
}

async function loadExecutionQueue() {
  state.executionQueue = {
    status: await getJson("/api/execution-queue"),
    jobs: await getJson("/api/execution-queue/jobs?limit=5"),
  };
  renderExecutionQueue();
}

async function enqueueExecutionQueueJob() {
  els.executionQueueStatus.textContent = "Enqueuing controlled execution...";
  state.executionQueueJob = await postJson("/api/execution-queue/enqueue", {
    profile_id: "osm_tag_quality",
    target_workspace_id: DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID,
    execute_now: true,
  });
  await loadExecutionQueue();
  await loadOsmTagQuality();
  await loadProfileWorkspaces();
}

function renderDatasetPackages() {
  const payload = state.datasetPackages;
  if (!payload || !payload.status) {
    els.datasetPackagesStatus.textContent = "No dataset package data loaded.";
    els.datasetPackagesBody.innerHTML = "";
    return;
  }
  const status = payload.status;
  const pkg = state.datasetPackage;
  els.datasetPackagesStatus.textContent = `${status.package_count || 0} packages; ${status.source_count || 0} sources`;
  els.datasetPackagesBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(status.dataset_package_version || "")}</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Latest package:</b> ${escapeHtml(pkg ? pkg.package_id || "" : "none")}</p>
      <p><b>Queue status:</b> ${escapeHtml(pkg ? pkg.execution_queue_status || "" : "")}</p>
      ${pkg ? `<a href="/api/dataset-packages/packages/${encodeURIComponent(pkg.package_id)}/download">Download report</a>` : ""}
    </div>
  `;
}

async function loadDatasetPackages() {
  state.datasetPackages = {
    status: await getJson("/api/dataset-packages"),
    packages: await getJson("/api/dataset-packages/packages?limit=5"),
  };
  renderDatasetPackages();
}

async function createDatasetPackage() {
  els.datasetPackagesStatus.textContent = "Creating dataset package...";
  state.datasetPackage = await postJson("/api/dataset-packages/create", {
    dataset_id: "israel-and-palestine-260521-free-shp-zip",
    template_id: "generic_osm_tag_coverage",
    queue_profile_id: "osm_tag_quality",
    target_workspace_id: DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID,
  });
  await loadDatasetPackages();
  await loadExecutionQueue();
}

async function loadPilotAreas() {
  const params = new URLSearchParams();
  params.set("limit", "80");
  const q = els.pilotSearch.value.trim();
  if (q) params.set("q", q);
  state.pilotMetadata = await getJson("/api/pilot-areas/metadata");
  state.pilots = await getJson(`/api/pilot-areas?${params.toString()}`);
  renderPilotAreas();
  await loadPilotPreflight();
  await loadAnalysisProfiles();
}

async function loadPilotPreflight() {
  const pilot = selectedPilot();
  if (!pilot) {
    state.pilotPreflight = null;
    renderPilotPreflight();
    state.analysisPlan = null;
    renderAnalysisWorkflow();
    return;
  }
  const params = new URLSearchParams();
  params.set("pilot_osm_id", pilot.osm_id);
  params.set("dataset_id", els.sourceSelect.value || pilot.source_dataset_id);
  params.set("workspace_id", pilot.pbf_enriched_workspace_id);
  params.set("route_workspace_id", pilot.route_aware_workspace_id);
  params.set("route_aware", els.pilotRouteAware.checked ? "true" : "false");
  state.pilotPreflight = await getJson(`/api/preflight/safe-access-pilot?${params.toString()}`);
  renderPilotPreflight();
  await planAnalysisWorkflow(true);
}

function analysisWorkflowPayload() {
  const pilot = selectedPilot();
  if (!pilot) return null;
  return {
    dataset_id: els.sourceSelect.value || pilot.source_dataset_id,
    pilot_osm_id: pilot.osm_id,
    pilot_name: pilot.name,
    template_id: els.templateSelect.value || "safe_access",
    workspace_id: pilot.pbf_enriched_workspace_id,
    route_workspace_id: pilot.route_aware_workspace_id,
    route_aware: els.pilotRouteAware.checked,
  };
}

async function planAnalysisWorkflow(silent = false) {
  const payload = analysisWorkflowPayload();
  if (!payload) {
    state.analysisPlan = null;
    renderAnalysisWorkflow();
    return;
  }
  if (!silent) els.analysisWorkflowStatus.textContent = "Planning selected analysis...";
  state.analysisPlan = await postJson("/api/analysis-workflow/plan", payload);
  renderAnalysisWorkflow();
}

async function startAnalysisWorkflow() {
  const payload = analysisWorkflowPayload();
  if (!payload) {
    els.analysisWorkflowStatus.textContent = "No pilot area selected.";
    return;
  }
  if (!state.analysisPlan || !state.analysisPlan.can_start_job) {
    await planAnalysisWorkflow(true);
  }
  if (state.analysisPlan && state.analysisPlan.can_start_job === false) {
    els.analysisWorkflowStatus.textContent = "Analysis is not ready. Review the blockers in the plan.";
    return;
  }
  els.analysisWorkflowStatus.textContent = "Starting analysis workflow job...";
  const result = await postJson("/api/analysis-workflow/start", payload);
  if (!result.ok) {
    els.analysisWorkflowStatus.textContent = `Analysis start failed: ${result.error || "unknown error"}`;
    state.analysisPlan = result.plan || state.analysisPlan;
    renderAnalysisWorkflow();
    return;
  }
  state.analysisPlan = result.plan;
  renderAnalysisWorkflow();
  els.analysisWorkflowStatus.textContent = `Analysis job queued: ${result.job.job_id}`;
  await loadJobs();
  await loadAnalysisRuns();
  await pollJob(result.job.job_id);
}

async function buildWorkspace() {
  const datasetId = els.sourceSelect.value;
  if (!datasetId) return;
  els.buildStatus.textContent = "Running template builder...";
  const result = await postJson("/api/runs/safe-access-kfar-saba", { dataset_id: datasetId });
  if (!result.ok) {
    els.buildStatus.textContent = `Build failed: ${result.error || "unknown error"}`;
    return;
  }
  const action = result.created ? "created" : "already exists";
  els.buildStatus.textContent = `Workspace ${action}: ${result.workspace.manifest.workspace_id}`;
  state.activeWorkspaceId = result.workspace.manifest.workspace_id;
  await loadWorkspaceRegistry();
  await loadDashboardWorkspace();
}

async function buildGenericWorkspace() {
  const datasetId = els.sourceSelect.value;
  if (!datasetId) return;
  els.buildStatus.textContent = "Running PBF-enriched Geofabrik mapper...";
  const result = await postJson("/api/runs/safe-access-generic", {
    dataset_id: datasetId,
    pilot_osm_id: "53796999",
    pilot_name: "Kfar Saba",
    workspace_id: "safe_access_kfar_saba_pbf_enriched_v001",
  });
  if (!result.ok) {
    els.buildStatus.textContent = `Generic build failed: ${result.error || "unknown error"}`;
    return;
  }
  const action = result.created ? "created" : "already exists";
  els.buildStatus.textContent = `PBF-enriched workspace ${action}: ${result.workspace.manifest.workspace_id}`;
  state.activeWorkspaceId = result.workspace.manifest.workspace_id;
  await loadWorkspaceRegistry();
  await loadDashboardWorkspace();
}

async function buildRouteAwareWorkspace() {
  els.buildStatus.textContent = "Running route-aware network proxy analysis...";
  const result = await postJson("/api/runs/route-aware-kfar-saba", {
    base_workspace_id: "safe_access_kfar_saba_pbf_enriched_v001",
    workspace_id: "safe_access_kfar_saba_route_aware_v001",
  });
  if (!result.ok) {
    els.buildStatus.textContent = `Route-aware build failed: ${result.error || "unknown error"}`;
    return;
  }
  const action = result.created ? "created" : "already exists";
  els.buildStatus.textContent = `Route-aware workspace ${action}: ${result.workspace.manifest.workspace_id}`;
  state.activeWorkspaceId = result.workspace.manifest.workspace_id;
  await loadWorkspaceRegistry();
  await loadDashboardWorkspace();
}

async function buildPilotWorkspace() {
  const pilot = selectedPilot();
  if (!pilot) {
    els.pilotStatus.textContent = "No pilot area selected.";
    return;
  }
  if (state.pilotPreflight && state.pilotPreflight.can_start_job === false) {
    els.pilotStatus.textContent = "Preflight blocks this pilot build. Check missing source requirements.";
    return;
  }
  els.pilotStatus.textContent = `Starting background job for ${pilot.name}...`;
  const job = await postJson("/api/jobs/safe-access-pilot", {
    dataset_id: els.sourceSelect.value || pilot.source_dataset_id,
    pilot_osm_id: pilot.osm_id,
    pilot_name: pilot.name,
    workspace_id: pilot.pbf_enriched_workspace_id,
    route_workspace_id: pilot.route_aware_workspace_id,
    route_aware: els.pilotRouteAware.checked,
  });
  if (job.error) {
    els.pilotStatus.textContent = `Pilot job failed to start: ${job.error}`;
    return;
  }
  els.pilotStatus.textContent = `Job queued: ${job.job_id}`;
  await loadJobs();
  await pollJob(job.job_id);
}

function renderProfileDashboardOptions() {
  const profiles = state.profileDashboard && state.profileDashboard.profiles ? state.profileDashboard.profiles : [];
  if (!profiles.length) {
    els.profileDashboardSelect.innerHTML = `<option value="">No profiles</option>`;
    return;
  }
  const current = els.profileDashboardSelect.value || profiles[0].profile_id;
  els.profileDashboardSelect.innerHTML = profiles
    .map((profile) => `<option value="${escapeHtml(profile.profile_id)}">${escapeHtml(typeLabel(profile.profile_id))}</option>`)
    .join("");
  els.profileDashboardSelect.value = profiles.some((profile) => profile.profile_id === current) ? current : profiles[0].profile_id;
}

function renderProfileDashboard() {
  const summary = state.profileDashboardSummary || {};
  const payload = state.profileDashboardResults || {};
  const rows = payload.rows || [];
  if (!summary.ok || !payload.ok) {
    els.profileDashboardStatus.textContent = "Profile dashboard unavailable.";
    els.profileResultsStatus.textContent = "No profile";
    els.profileDashboardBody.innerHTML = `<p class="note">Normalized profile results are not available.</p>`;
    els.profileResultRows.innerHTML = "";
    return;
  }
  els.profileDashboardStatus.textContent = `${summary.result_count.toLocaleString()} rows; ${summary.high_priority_count.toLocaleString()} high-priority review rows`;
  els.profileResultsStatus.textContent = `${typeLabel(summary.profile_id)}; ${payload.contract_version}`;
  els.profileDashboardBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(typeLabel(summary.profile_id))}</h3>
      <p><b>Workspace:</b> ${escapeHtml(summary.workspace_id)}</p>
      <p><b>Rows:</b> ${Number(summary.result_count || 0).toLocaleString()}</p>
      <p><b>Median score:</b> ${fmt(summary.median_primary_score)}</p>
      <p><b>Route &gt;250 m:</b> ${Number(summary.route_over_250m_count || 0).toLocaleString()}</p>
    </div>
  `;
  els.profileResultRows.innerHTML = rows
    .map((row) => `
      <tr>
        <td>${escapeHtml(typeLabel(row.profile_id))}</td>
        <td>${escapeHtml(row.result_id)}</td>
        <td>${escapeHtml(typeLabel(row.entity_type))}</td>
        <td>${escapeHtml(row.name || "Unnamed")}</td>
        <td>${fmt(row.nearest_crossing_m)}</td>
        <td>${fmt(row.route_nearest_crossing_m)}</td>
        <td>${fmt(row.nearest_major_road_m)}</td>
        <td>${Number(row.primary_score || 0).toLocaleString()}</td>
        <td>${escapeHtml((row.flags || []).slice(0, 3).join(", "))}</td>
      </tr>
    `)
    .join("");
}

function renderProductArchitecture() {
  const architecture = state.productArchitecture;
  if (!architecture || architecture.error) {
    els.productArchitectureStatus.textContent = "Architecture unavailable.";
    els.architectureStatus.textContent = "No blueprint";
    els.productArchitectureBody.innerHTML = `<p class="note">Product architecture evidence is not available.</p>`;
    els.productArchitecturePanel.innerHTML = `<p class="note">Product architecture evidence is not available.</p>`;
    return;
  }
  const evidence = architecture.current_evidence || {};
  const variants = architecture.top_project_variants || [];
  const pipeline = architecture.canonical_pipeline || [];
  const roadmap = architecture.roadmap || [];
  els.productArchitectureStatus.textContent = `${evidence.implemented_profile_count || 0} implemented profiles; recommended: ${typeLabel(architecture.recommended_variant_id || "")}`;
  els.architectureStatus.textContent = architecture.product_architecture_version || "ready";
  els.productArchitectureBody.innerHTML = `
    <div class="workspace-card">
      <h3>${escapeHtml(architecture.product_name || "GeoReview Studio")}</h3>
      <p><b>Recommended:</b> ${escapeHtml(typeLabel(architecture.recommended_variant_id || ""))}</p>
      <p><b>Profiles:</b> ${Number(evidence.implemented_profile_count || 0).toLocaleString()} implemented / ${Number(evidence.analysis_profile_count || 0).toLocaleString()} listed</p>
      <p><b>Pilot:</b> ${escapeHtml(evidence.default_pilot || "")}</p>
      <p><b>Next:</b> ${escapeHtml(architecture.best_next_development_step || "")}</p>
    </div>
  `;
  els.productArchitecturePanel.innerHTML = `
    <div class="profile-grid">
      <div class="profile-card">
        <h3>Top Project Options</h3>
        ${variants.slice(0, 3).map((variant) => `
          <p><b>${escapeHtml(variant.name)}:</b> ${escapeHtml(variant.portfolio_strength)} - ${escapeHtml(variant.current_fit)}</p>
        `).join("")}
      </div>
      <div class="profile-card">
        <h3>Pipeline</h3>
        <div class="mini-table">
          ${pipeline.map((stage) => `
            <div class="mini-row">
              <span>${escapeHtml(stage.name)}</span>
              <b>${escapeHtml(stage.status)}</b>
              <em>${Number(stage.stage || 0).toLocaleString()}</em>
            </div>
          `).join("")}
        </div>
      </div>
      <div class="profile-card">
        <h3>Roadmap</h3>
        ${roadmap.slice(0, 5).map((item) => `<p><b>${escapeHtml(item.release)}:</b> ${escapeHtml(item.theme)} - ${escapeHtml(item.status)}</p>`).join("")}
      </div>
    </div>
  `;
}

function renderPilotPreflight() {
  const preflight = state.pilotPreflight;
  if (!preflight || preflight.error) {
    els.pilotPreflight.innerHTML = `<p class="small-note">Preflight unavailable for the current pilot selection.</p>`;
    return;
  }
  const pilot = preflight.pilot || {};
  const workspaces = preflight.workspaces || {};
  const estimate = preflight.estimate || {};
  const layers = preflight.required_layers || [];
  const readyLayers = layers.filter((layer) => layer.present).length;
  const activeStatus = workspaces.active_workspace_exists ? "ready" : "will build";
  els.pilotPreflight.innerHTML = `
    <div class="preflight-head">
      <b>${escapeHtml(preflight.can_start_job ? "Ready to run" : "Needs source check")}</b>
      <span>${escapeHtml(estimate.runtime_class || "unknown")}</span>
    </div>
    <p><b>Pilot:</b> ${escapeHtml(pilot.name)} (${escapeHtml(pilot.fclass || "")}; ${Number(pilot.population || 0).toLocaleString()})</p>
    <p><b>BBox:</b> ${fmt(pilot.bbox && pilot.bbox.approx_width_km, " km")} x ${fmt(pilot.bbox && pilot.bbox.approx_height_km, " km")}</p>
    <p><b>Active workspace:</b> ${escapeHtml(workspaces.active_workspace_id || "")} (${activeStatus})</p>
    <p><b>Layers:</b> ${readyLayers}/${layers.length} expected; <b>PBF:</b> ${preflight.pbf_enrichment && preflight.pbf_enrichment.available ? "available" : "missing"}</p>
    <p><b>Operation:</b> ${escapeHtml(typeLabel(estimate.expected_operation || ""))}</p>
    ${(preflight.warnings || []).slice(0, 3).map((item) => `<p class="small-note">- ${escapeHtml(item)}</p>`).join("")}
  `;
}

function renderAnalysisWorkflow() {
  const plan = state.analysisPlan;
  if (!plan || plan.error) {
    els.analysisWorkflowStatus.textContent = plan && plan.error ? `Plan error: ${plan.error}` : "No analysis plan loaded.";
    els.analysisWorkflowBody.innerHTML = `<p class="small-note">Select a source, pilot area, and template to create an analysis plan.</p>`;
    return;
  }
  const steps = plan.steps || [];
  els.analysisWorkflowStatus.textContent = plan.can_start_job
    ? `Ready: ${plan.active_workspace_id}`
    : `Blocked: ${(plan.blockers || []).join(", ") || "check plan"}`;
  els.analysisWorkflowBody.innerHTML = `
    <div class="preflight-head">
      <b>${escapeHtml(plan.can_start_job ? "Ready to start" : "Blocked")}</b>
      <span>${escapeHtml(plan.template_id || "")}</span>
    </div>
    <p><b>Source:</b> ${escapeHtml(plan.source && plan.source.file_name)} (${escapeHtml(plan.source && plan.source.readiness_level)})</p>
    <p><b>Pilot:</b> ${escapeHtml(plan.pilot && plan.pilot.name)}; <b>Route-aware:</b> ${plan.route_aware ? "yes" : "no"}</p>
    <p><b>Active workspace:</b> ${escapeHtml(plan.active_workspace_id || "")}</p>
    ${steps.map((step) => `<p><b>${escapeHtml(typeLabel(step.step))}:</b> ${escapeHtml(step.status)} - ${escapeHtml(step.evidence || "")}</p>`).join("")}
    ${(plan.blockers || []).map((blocker) => `<p class="small-note">- ${escapeHtml(blocker)}</p>`).join("")}
  `;
}

function renderSourceProfile() {
  const profile = state.sourceProfile;
  if (!profile || profile.error) {
    els.profileStatus.textContent = "No profile";
    els.sourceProfile.innerHTML = `<p class="note">Dataset profile is not available.</p>`;
    return;
  }
  const dataset = profile.dataset;
  els.profileStatus.textContent = dataset.profile_status;
  els.sourceHint.textContent = `${dataset.file_name}; ${dataset.layer_count} layers; ${dataset.size_mb.toFixed(1)} MB`;
  const topLayers = profile.layers.slice(0, 8);
  const importantTags = profile.tag_summary.important_categories.slice(0, 8);
  els.sourceProfile.innerHTML = `
    <div class="profile-card">
      <h3>Source</h3>
      <p><b>Format:</b> ${escapeHtml(dataset.extension)}</p>
      <p><b>Role:</b> ${escapeHtml(dataset.likely_role)}</p>
      <p><b>QGIS:</b> ${escapeHtml(dataset.suitability.qgis)}</p>
      <p><b>Python:</b> ${escapeHtml(dataset.suitability.python_geopandas)}</p>
      <p><b>PostGIS:</b> ${escapeHtml(dataset.suitability.postgis)}</p>
    </div>
    <div class="profile-card">
      <h3>Layer Types</h3>
      ${Object.entries(profile.geometry_types)
        .map(([key, value]) => `<p><b>${escapeHtml(key)}:</b> ${value}</p>`)
        .join("") || `<p class="note">No layer summary rows found.</p>`}
    </div>
    <div class="profile-card wide">
      <h3>Top Layers</h3>
      <div class="mini-table">
        ${topLayers
          .map((layer) => `
            <div class="mini-row">
              <span>${escapeHtml(layer.layer)}</span>
              <b>${escapeHtml(layer.geometry_type)}</b>
              <em>${layer.feature_count.toLocaleString()}</em>
            </div>
          `)
          .join("") || `<p class="note">Layer details are not available.</p>`}
      </div>
    </div>
    <div class="profile-card wide">
      <h3>Important Tag Evidence</h3>
      <div class="tag-grid">
        ${importantTags
          .map((tag) => `
            <div class="tag-item">
              <span>${escapeHtml(typeLabel(tag.category))}</span>
              <b>${Number(tag.total_count).toLocaleString()}</b>
            </div>
          `)
          .join("") || `<p class="note">Important tag counts are not available for this source.</p>`}
      </div>
    </div>
  `;
}

function renderTemplateCheck() {
  const check = state.templateCheck;
  if (!check || check.error) {
    els.templateStatus.textContent = "No check";
    els.templateReadiness.innerHTML = `<p class="note">Template readiness check is not available.</p>`;
    return;
  }
  const readiness = check.readiness;
  els.templateStatus.textContent = readiness.level;
  els.templateReadiness.innerHTML = `
    <p><b>Readiness:</b> ${escapeHtml(readiness.level)}</p>
    <p><b>Evidence:</b> ${escapeHtml(JSON.stringify(readiness.evidence))}</p>
    <p><b>Limitation:</b> ${escapeHtml(readiness.limitation)}</p>
    <p><b>Next step:</b> ${escapeHtml(readiness.next_step)}</p>
    <p class="note">${escapeHtml(check.recommendation)}</p>
  `;
}

function renderSourceOnboarding() {
  const onboarding = state.sourceOnboarding;
  if (!onboarding) {
    els.sourceOnboardingStatus.textContent = "No source scan loaded.";
    els.sourceOnboardingBody.innerHTML = "";
    return;
  }
  const status = onboarding.status || {};
  const sources = onboarding.sources || [];
  els.sourceOnboardingStatus.textContent = `${sources.length} local GIS sources; ${status.cached ? "cached" : "live scan"}`;
  els.sourceOnboardingBody.innerHTML = sources
    .map((source) => {
      const readiness = source.readiness || {};
      const blockers = readiness.blockers || [];
      const templates = readiness.supported_templates || [];
      return `
        <div class="workspace-card">
          <h3>${escapeHtml(source.file_name)}</h3>
          <p><b>Readiness:</b> ${escapeHtml(readiness.level || "")}</p>
          <p><b>Layers:</b> ${source.layers ? source.layers.length : 0}; <b>Size:</b> ${Number(source.size_mb || 0).toFixed(1)} MB</p>
          <p><b>Templates:</b> ${escapeHtml(templates.join(", ") || "none yet")}</p>
          ${blockers.length ? `<p><b>Blockers:</b> ${escapeHtml(blockers.slice(0, 2).join(", "))}</p>` : `<p><b>Blockers:</b> none</p>`}
        </div>
      `;
    })
    .join("");
}

function renderLocalIntake() {
  const intake = state.localIntake;
  const preview = state.localIntakePreview;
  const plan = state.localIntakePlan;
  if (!intake) {
    els.localIntakeStatus.textContent = "No local intake status loaded.";
    els.localIntakeBody.innerHTML = "";
    return;
  }
  const status = intake.status || {};
  const sources = (intake.sources && intake.sources.sources) || [];
  els.localIntakeStatus.textContent = `${status.source_count || sources.length} sources available for reviewed intake`;
  const previewSource = preview && preview.source ? preview.source : null;
  const actions = (preview && preview.recommended_next_actions) || [];
  els.localIntakeBody.innerHTML = `
    <div class="workspace-card">
      <h3>Read-only intake</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "reviewed local intake")}</p>
      <p><b>Output:</b> ${escapeHtml(status.intake_dir || "")}</p>
      <p><b>Formats:</b> ${escapeHtml((status.supported_extensions || []).join(", "))}</p>
    </div>
    ${previewSource ? `
      <div class="workspace-card">
        <h3>${escapeHtml(previewSource.file_name || previewSource.dataset_id)}</h3>
        <p><b>Input:</b> ${escapeHtml(preview.input_type || "")}</p>
        <p><b>Readiness:</b> ${escapeHtml(previewSource.readiness_level || "")}</p>
        <p><b>Layers:</b> ${previewSource.layer_count || 0}; <b>Size:</b> ${Number(previewSource.size_mb || 0).toFixed(1)} MB</p>
        <p><b>Next:</b> ${escapeHtml(actions.join(" "))}</p>
      </div>
    ` : preview && preview.error ? `
      <div class="workspace-card">
        <h3>Preview blocked</h3>
        <p><b>Error:</b> ${escapeHtml(preview.error)}</p>
        <p>${escapeHtml(preview.detail || preview.path || "")}</p>
      </div>
    ` : `<p class="note">Preview a registered source path before creating an intake plan.</p>`}
    ${plan && plan.plan_file ? `
      <div class="workspace-card">
        <h3>Plan created</h3>
        <p><b>Plan:</b> ${escapeHtml(plan.plan_id)}</p>
        <p><b>File:</b> ${escapeHtml(plan.plan_file)}</p>
      </div>
    ` : ""}
  `;
}


function renderSourceImportGuardrails() {
  const payload = state.sourceImportGuardrails;
  const preview = state.sourceImportPreview;
  const request = state.sourceImportRequest;
  const decision = state.sourceImportDecision;
  if (!payload) {
    els.sourceImportGuardrailsStatus.textContent = "No source import guardrails loaded.";
    els.sourceImportGuardrailsBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const requests = payload.requests || [];
  const summary = preview && preview.summary ? preview.summary : {};
  els.sourceImportGuardrailsStatus.textContent = `${status.reviewable_source_count || 0} reviewable sources; ${status.request_count || requests.length || 0} review packets; ${status.approved_request_count || 0} approved`;
  const guardrails = (preview && preview.guardrails) || [];
  els.sourceImportGuardrailsBody.innerHTML = `
    <div class="workspace-card">
      <h3>Guardrail status</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Approval phrase:</b> ${escapeHtml(status.approval_phrase || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${preview ? `
      <div class="workspace-card">
        <h3>Preview</h3>
        <p><b>Readiness:</b> ${escapeHtml(preview.import_readiness || preview.error || "")}</p>
        <p><b>Hard failures:</b> ${summary.hard_failed_count || 0}; <b>Warnings:</b> ${summary.warning_guardrails || 0}</p>
        <p><b>Source:</b> ${escapeHtml(preview.source && (preview.source.file_name || preview.source.dataset_id))}</p>
        ${guardrails.length ? `<p><b>Guardrails:</b> ${escapeHtml(guardrails.slice(0, 4).map((gate) => `${gate.guardrail_id}:${gate.status}`).join(", "))}</p>` : ""}
      </div>
    ` : `<p class="note">Preview guardrails for the selected local source before creating a review packet.</p>`}
    ${request ? `
      <div class="workspace-card">
        <h3>Review packet</h3>
        <p><b>Request:</b> ${escapeHtml(request.request_id)}</p>
        <p><b>State:</b> ${escapeHtml(request.approval_state || request.review_readiness || "")}</p>
        <p><b>Markdown:</b> ${escapeHtml(request.files && request.files.markdown)}</p>
      </div>
    ` : ""}
    ${decision ? `
      <div class="workspace-card">
        <h3>Latest decision</h3>
        <p><b>Decision:</b> ${escapeHtml(decision.decision_state)}</p>
        <p><b>Can create metadata handoff:</b> ${decision.can_create_metadata_handoff ? "yes" : "no"}</p>
      </div>
    ` : ""}
    ${requests.length ? `
      <div class="workspace-card">
        <h3>Recent review packets</h3>
        ${requests.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.request_id)}</b><br />${escapeHtml(row.file_name || row.dataset_id || "")}; ${escapeHtml(row.latest_decision_state || row.approval_state || "")}</p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderSourceHandoff() {
  const payload = state.sourceHandoff;
  const created = state.sourceHandoffCreated;
  if (!payload) {
    els.sourceHandoffStatus.textContent = "No source handoff data loaded.";
    els.sourceHandoffBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const candidates = payload.candidates || [];
  const handoffs = payload.handoffs || [];
  els.sourceHandoffStatus.textContent = `${status.candidate_count || candidates.length || 0} approved candidates; ${status.handoff_count || handoffs.length || 0} handoffs; ${status.ready_handoff_count || 0} ready`;
  els.sourceHandoffBody.innerHTML = `
    <div class="workspace-card">
      <h3>Handoff status</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created handoff</h3>
        <p><b>Handoff:</b> ${escapeHtml(created.handoff_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.handoff_readiness)}</p>
        <p><b>Mapper:</b> ${escapeHtml(created.mapper_plan_id || "")}</p>
        <p><b>Dry run:</b> ${escapeHtml(created.contract_dry_run_id || "")}</p>
        <p><b>Queue:</b> ${escapeHtml(created.queue_job_id || "")}; ${escapeHtml(created.queue_status || "")}</p>
      </div>
    ` : `<p class="note">Create a planned handoff after approving a source import review packet.</p>`}
    ${candidates.length ? `
      <div class="workspace-card">
        <h3>Approved candidates</h3>
        ${candidates.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.request_id)}</b><br />${escapeHtml(row.file_name || row.dataset_id || "")}; profile ${escapeHtml(row.recommended_profile_id || "")}</p>`).join("")}
      </div>
    ` : ""}
    ${handoffs.length ? `
      <div class="workspace-card">
        <h3>Recent handoffs</h3>
        ${handoffs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.handoff_id)}</b><br />${escapeHtml(row.handoff_readiness || "")}; queue ${escapeHtml(row.queue_status || "")}</p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderSourceHandoffExecution() {
  const payload = state.sourceHandoffExecution;
  const created = state.sourceHandoffExecutionCreated;
  if (!payload) {
    els.sourceHandoffExecutionStatus.textContent = "No source handoff execution data loaded.";
    els.sourceHandoffExecutionBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const candidates = payload.candidates || [];
  const executions = payload.executions || [];
  els.sourceHandoffExecutionStatus.textContent = `${status.candidate_count || candidates.length || 0} ready handoffs; ${status.execution_count || executions.length || 0} executions; ${status.successful_execution_count || 0} verified`;
  els.sourceHandoffExecutionBody.innerHTML = `
    <div class="workspace-card">
      <h3>Execution status</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Ack phrase:</b> ${escapeHtml(status.execution_ack_phrase || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created execution</h3>
        <p><b>Execution:</b> ${escapeHtml(created.execution_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.execution_readiness)}</p>
        <p><b>Queue:</b> ${escapeHtml(created.execution_queue_job_id || "")}; ${escapeHtml(created.execution_status || "")}</p>
        <p><b>Workspace:</b> ${escapeHtml(created.generated_workspace_id || "")}</p>
        <p><b>Comparison:</b> ${escapeHtml(created.comparison && created.comparison.comparison_readiness)}</p>
      </div>
    ` : `<p class="note">Execute a ready handoff only after the source import approval and planned handoff evidence exist.</p>`}
    ${candidates.length ? `
      <div class="workspace-card">
        <h3>Ready handoffs</h3>
        ${candidates.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.handoff_id)}</b><br />${escapeHtml(row.profile_id || "")}; target ${escapeHtml(row.target_workspace_id || "")}</p>`).join("")}
      </div>
    ` : ""}
    ${executions.length ? `
      <div class="workspace-card">
        <h3>Recent executions</h3>
        ${executions.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.execution_id)}</b><br />${escapeHtml(row.execution_readiness || "")}; workspace ${escapeHtml(row.generated_workspace_id || "")}</p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderExecutionEvidencePackage() {
  const payload = state.executionEvidencePackage;
  const created = state.executionEvidencePackageCreated;
  if (!payload) {
    els.executionEvidencePackageStatus.textContent = "No execution evidence package data loaded.";
    els.executionEvidencePackageBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const candidates = payload.candidates || [];
  const packages = payload.packages || [];
  els.executionEvidencePackageStatus.textContent = `${status.candidate_count || candidates.length || 0} verified executions; ${status.package_count || packages.length || 0} packages; ${status.ready_package_count || 0} ready`;
  els.executionEvidencePackageBody.innerHTML = `
    <div class="workspace-card">
      <h3>Package status</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created package</h3>
        <p><b>Package:</b> ${escapeHtml(created.package_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.package_readiness)}</p>
        <p><b>Execution:</b> ${escapeHtml(created.execution_id || "")}</p>
        <p><b>Workspace:</b> ${escapeHtml(created.generated_workspace_id || "")}</p>
        <a href="/api/execution-evidence-package/packages/${encodeURIComponent(created.package_id)}/download">Download package</a>
      </div>
    ` : `<p class="note">Create a reviewer-ready package after a source handoff execution is verified.</p>`}
    ${candidates.length ? `
      <div class="workspace-card">
        <h3>Verified execution candidates</h3>
        ${candidates.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.execution_id)}</b><br />${escapeHtml(row.profile_id || "")}; workspace ${escapeHtml(row.generated_workspace_id || "")}</p>`).join("")}
      </div>
    ` : ""}
    ${packages.length ? `
      <div class="workspace-card">
        <h3>Recent packages</h3>
        ${packages.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.package_id)}</b><br />${escapeHtml(row.package_readiness || "")}; execution ${escapeHtml(row.execution_id || "")}<br /><a href="/api/execution-evidence-package/packages/${encodeURIComponent(row.package_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderExecutionResultDiff() {
  const payload = state.executionResultDiff;
  const created = state.executionResultDiffCreated;
  if (!payload) {
    els.executionResultDiffStatus.textContent = "No execution result diff data loaded.";
    els.executionResultDiffBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const candidates = payload.candidates || [];
  const diffs = payload.diffs || [];
  els.executionResultDiffStatus.textContent = `${status.candidate_pair_count || candidates.length || 0} candidate pairs; ${status.diff_count || diffs.length || 0} diffs; ${status.ready_diff_count || 0} ready`;
  els.executionResultDiffBody.innerHTML = `
    <div class="workspace-card">
      <h3>Diff status</h3>
      <p><b>Mode:</b> ${escapeHtml(status.mode || "")}</p>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Packages:</b> ${escapeHtml(status.package_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created diff</h3>
        <p><b>Diff:</b> ${escapeHtml(created.diff_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.diff_readiness)}</p>
        <p><b>Classification:</b> ${escapeHtml(created.diff_classification || "")}</p>
        <p><b>Scope:</b> ${escapeHtml(created.comparison_scope || "")}</p>
        <a href="/api/execution-result-diff/diffs/${encodeURIComponent(created.diff_id)}/download">Download diff</a>
      </div>
    ` : `<p class="note">Create a result diff after at least two execution evidence packages are ready.</p>`}
    ${candidates.length ? `
      <div class="workspace-card">
        <h3>Diff candidates</h3>
        ${candidates.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.comparison_scope || "")}</b><br />${escapeHtml(row.left_package_id || "")}<br />vs ${escapeHtml(row.right_package_id || "")}</p>`).join("")}
      </div>
    ` : ""}
    ${diffs.length ? `
      <div class="workspace-card">
        <h3>Recent diffs</h3>
        ${diffs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.diff_id)}</b><br />${escapeHtml(row.diff_readiness || "")}; ${escapeHtml(row.diff_classification || "")}<br /><a href="/api/execution-result-diff/diffs/${encodeURIComponent(row.diff_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderExecutionDiffGallery() {
  const payload = state.executionDiffGallery;
  const created = state.executionDiffGalleryCreated;
  if (!payload) {
    els.executionDiffGalleryStatus.textContent = "No execution diff gallery data loaded.";
    els.executionDiffGalleryBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const items = payload.items || [];
  const galleries = payload.galleries || [];
  const classificationCounts = status.classification_counts || {};
  els.executionDiffGalleryStatus.textContent = `${status.indexed_diff_count || items.length || 0} indexed diffs; ${status.ready_diff_count || 0} ready; ${status.review_queue_count || 0} review queue`;
  els.executionDiffGalleryBody.innerHTML = `
    <div class="workspace-card">
      <h3>Gallery status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest diff:</b> ${escapeHtml(status.latest_diff_id || "")}</p>
      <p><b>Classification counts:</b> ${escapeHtml(JSON.stringify(classificationCounts))}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created gallery</h3>
        <p><b>Gallery:</b> ${escapeHtml(created.gallery_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.gallery_readiness)}</p>
        <p><b>Items:</b> ${escapeHtml(created.item_count || 0)}</p>
        <p><b>Review queue:</b> ${escapeHtml(created.review_queue_count || 0)}</p>
        <a href="/api/execution-diff-gallery/galleries/${encodeURIComponent(created.gallery_id)}/download">Download gallery</a>
      </div>
    ` : `<p class="note">Create a gallery artifact after execution result diffs are available.</p>`}
    ${items.length ? `
      <div class="workspace-card">
        <h3>Indexed diffs</h3>
        ${items.slice(0, 5).map((row) => `<p><b>${escapeHtml(row.diff_id)}</b><br />${escapeHtml(row.portfolio_label || "")}; ${escapeHtml(row.diff_classification || "")}; priority ${escapeHtml(row.review_priority || 0)}<br /><a href="${escapeHtml(row.download_url || "#")}">Download diff</a></p>`).join("")}
      </div>
    ` : ""}
    ${galleries.length ? `
      <div class="workspace-card">
        <h3>Recent galleries</h3>
        ${galleries.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.gallery_id)}</b><br />${escapeHtml(row.gallery_readiness || "")}; items ${escapeHtml(row.item_count || 0)}<br /><a href="/api/execution-diff-gallery/galleries/${encodeURIComponent(row.gallery_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderExecutionDiffDetail() {
  const payload = state.executionDiffDetail;
  const created = state.executionDiffDetailCreated;
  if (!payload) {
    els.executionDiffDetailStatus.textContent = "No execution diff detail data loaded.";
    els.executionDiffDetailBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const baselines = payload.baselines || [];
  const drilldowns = payload.drilldowns || [];
  els.executionDiffDetailStatus.textContent = `${status.baseline_candidate_count || baselines.length || 0} baselines; ${status.detail_count || drilldowns.length || 0} drilldowns; ${status.ready_detail_count || 0} ready`;
  els.executionDiffDetailBody.innerHTML = `
    <div class="workspace-card">
      <h3>Detail status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Preferred baseline:</b> ${escapeHtml(status.preferred_baseline_id || "")}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created drilldown</h3>
        <p><b>Detail:</b> ${escapeHtml(created.detail_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.drilldown_readiness)}</p>
        <p><b>Diff:</b> ${escapeHtml(created.diff_id || "")}</p>
        <p><b>Baseline:</b> ${escapeHtml(created.baseline_diff_id || "")}</p>
        <a href="/api/execution-diff-detail/drilldowns/${encodeURIComponent(created.detail_id)}/download">Download drilldown</a>
      </div>
    ` : `<p class="note">Create a drilldown after at least one baseline candidate is available.</p>`}
    ${baselines.length ? `
      <div class="workspace-card">
        <h3>Baseline candidates</h3>
        ${baselines.slice(0, 4).map((row) => `<p><b>${escapeHtml(row.diff_id)}</b><br />score ${escapeHtml(row.baseline_score || 0)}; ${escapeHtml(row.diff_classification || "")}; ${escapeHtml(row.reason || "")}</p>`).join("")}
      </div>
    ` : ""}
    ${drilldowns.length ? `
      <div class="workspace-card">
        <h3>Recent drilldowns</h3>
        ${drilldowns.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.detail_id)}</b><br />${escapeHtml(row.drilldown_readiness || "")}; changed tables ${escapeHtml(row.changed_table_count || 0)}<br /><a href="/api/execution-diff-detail/drilldowns/${encodeURIComponent(row.detail_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderReproducibilityAuditPacket() {
  const payload = state.reproducibilityAuditPacket;
  const created = state.reproducibilityAuditPacketCreated;
  if (!payload) {
    els.reproducibilityAuditPacketStatus.textContent = "No reproducibility audit packet data loaded.";
    els.reproducibilityAuditPacketBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const candidates = payload.candidates || [];
  const packets = payload.packets || [];
  els.reproducibilityAuditPacketStatus.textContent = `${status.candidate_count || candidates.length || 0} candidates; ${status.packet_count || packets.length || 0} packets; ${status.ready_packet_count || 0} ready`;
  els.reproducibilityAuditPacketBody.innerHTML = `
    <div class="workspace-card">
      <h3>Packet status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
      <p><b>Source GIS modified:</b> ${status.source_gis_modified === false ? "false" : "check required"}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created packet</h3>
        <p><b>Packet:</b> ${escapeHtml(created.packet_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.packet_readiness)}</p>
        <p><b>Detail:</b> ${escapeHtml(created.detail_id || "")}</p>
        <p><b>Copied files:</b> ${escapeHtml((created.copied_files || []).length)}</p>
        <a href="/api/reproducibility-audit-packet/packets/${encodeURIComponent(created.packet_id)}/download">Download packet summary</a>
      </div>
    ` : `<p class="note">Create an audit packet after a ready execution diff detail exists.</p>`}
    ${candidates.length ? `
      <div class="workspace-card">
        <h3>Packet candidates</h3>
        ${candidates.slice(0, 4).map((row) => `<p><b>${escapeHtml(row.detail_id)}</b><br />diff ${escapeHtml(row.diff_id || "")}; changed tables ${escapeHtml(row.changed_table_count || 0)}; output deltas ${escapeHtml(row.output_delta_count || 0)}</p>`).join("")}
      </div>
    ` : ""}
    ${packets.length ? `
      <div class="workspace-card">
        <h3>Recent packets</h3>
        ${packets.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.packet_id)}</b><br />${escapeHtml(row.packet_readiness || "")}; files ${escapeHtml(row.copied_file_count || 0)}<br /><a href="/api/reproducibility-audit-packet/packets/${encodeURIComponent(row.packet_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderReviewerAuditIndex() {
  const payload = state.reviewerAuditIndex;
  const created = state.reviewerAuditIndexCreated;
  if (!payload) {
    els.reviewerAuditIndexStatus.textContent = "No reviewer audit index data loaded.";
    els.reviewerAuditIndexBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const indexes = payload.indexes || [];
  els.reviewerAuditIndexStatus.textContent = `${status.ready_packet_count || 0} ready packets; ${status.index_count || indexes.length || 0} indexes; ${status.ready_index_count || 0} ready`;
  els.reviewerAuditIndexBody.innerHTML = `
    <div class="workspace-card">
      <h3>Index status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Portfolio links:</b> ${escapeHtml(status.portfolio_link_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created index</h3>
        <p><b>Index:</b> ${escapeHtml(created.index_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.index_readiness)}</p>
        <p><b>Packets:</b> ${escapeHtml(created.ready_packet_count || 0)} / ${escapeHtml(created.packet_count || 0)}</p>
        <a href="/api/reviewer-audit-index/indexes/${encodeURIComponent(created.index_id)}/download">Download reviewer index</a>
      </div>
    ` : `<p class="note">Create a reviewer index after audit packets are ready.</p>`}
    ${indexes.length ? `
      <div class="workspace-card">
        <h3>Recent indexes</h3>
        ${indexes.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.index_id)}</b><br />${escapeHtml(row.index_readiness || "")}; packets ${escapeHtml(row.ready_packet_count || 0)}; links ${escapeHtml(row.portfolio_link_count || 0)}<br /><a href="/api/reviewer-audit-index/indexes/${encodeURIComponent(row.index_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderPortfolioExportLauncher() {
  const payload = state.portfolioExportLauncher;
  const created = state.portfolioExportLauncherCreated;
  if (!payload) {
    els.portfolioExportLauncherStatus.textContent = "No portfolio export launcher data loaded.";
    els.portfolioExportLauncherBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const launchers = payload.launchers || [];
  els.portfolioExportLauncherStatus.textContent = `${status.launch_target_count || 0} launch targets; ${status.launcher_count || launchers.length || 0} launchers; ${status.ready_launcher_count || 0} ready`;
  els.portfolioExportLauncherBody.innerHTML = `
    <div class="workspace-card">
      <h3>Launcher status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Reviewer indexes:</b> ${escapeHtml(status.reviewer_index_count || 0)}; <b>audit packets:</b> ${escapeHtml(status.audit_packet_count || 0)}</p>
      <p><b>Portfolio artifacts:</b> ${escapeHtml(status.portfolio_artifact_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created launcher</h3>
        <p><b>Launcher:</b> ${escapeHtml(created.launcher_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.launcher_readiness)}</p>
        <p><b>Targets:</b> ${escapeHtml(created.launch_target_count || 0)}</p>
        <a href="/api/portfolio-export-launcher/launchers/${encodeURIComponent(created.launcher_id)}/download">Download launcher summary</a>
      </div>
    ` : `<p class="note">Create a start-here launcher after reviewer index and audit packet artifacts exist.</p>`}
    ${launchers.length ? `
      <div class="workspace-card">
        <h3>Recent launchers</h3>
        ${launchers.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.launcher_id)}</b><br />${escapeHtml(row.launcher_readiness || "")}; targets ${escapeHtml(row.launch_target_count || 0)}<br /><a href="/api/portfolio-export-launcher/launchers/${encodeURIComponent(row.launcher_id)}/download">Download</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderPortableReleasePackage() {
  const payload = state.portableReleasePackage;
  const created = state.portableReleasePackageCreated;
  if (!payload) {
    els.portableReleasePackageStatus.textContent = "No portable release package data loaded.";
    els.portableReleasePackageBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const packages = payload.packages || [];
  els.portableReleasePackageStatus.textContent = `${status.ready_launcher_count || 0} ready launchers; ${status.package_count || packages.length || 0} packages; ${status.ready_package_count || 0} ready`;
  els.portableReleasePackageBody.innerHTML = `
    <div class="workspace-card">
      <h3>Package status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest file count:</b> ${escapeHtml(status.latest_package_file_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created package</h3>
        <p><b>Package:</b> ${escapeHtml(created.package_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.package_readiness)}</p>
        <p><b>Files:</b> ${escapeHtml(created.included_file_count || 0)}</p>
        <p><b>ZIP bytes:</b> ${escapeHtml(created.zip_size_bytes || 0)}</p>
        <a href="/api/portable-release-package/packages/${encodeURIComponent(created.package_id)}/download">Download package ZIP</a>
      </div>
    ` : `<p class="note">Create a portable release package after a ready launcher exists.</p>`}
    ${packages.length ? `
      <div class="workspace-card">
        <h3>Recent packages</h3>
        ${packages.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.package_id)}</b><br />${escapeHtml(row.package_readiness || "")}; files ${escapeHtml(row.included_file_count || 0)}; ZIP ${escapeHtml(row.zip_size_bytes || 0)} bytes<br /><a href="/api/portable-release-package/packages/${encodeURIComponent(row.package_id)}/download">Download ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderDemoScriptPack() {
  const payload = state.demoScriptPack;
  const created = state.demoScriptPackCreated;
  if (!payload) {
    els.demoScriptPackStatus.textContent = "No demo script pack data loaded.";
    els.demoScriptPackBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const packs = payload.packs || [];
  els.demoScriptPackStatus.textContent = `${status.ready_portable_package_count || 0} ready packages; ${status.pack_count || packs.length || 0} packs; ${status.ready_pack_count || 0} ready`;
  els.demoScriptPackBody.innerHTML = `
    <div class="workspace-card">
      <h3>Script pack status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Script steps:</b> ${escapeHtml(status.script_step_count || 0)}; <b>Screenshot targets:</b> ${escapeHtml(status.screenshot_target_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created script pack</h3>
        <p><b>Pack:</b> ${escapeHtml(created.pack_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.pack_readiness)}</p>
        <p><b>Steps:</b> ${escapeHtml(created.script_step_count || 0)}; <b>Targets:</b> ${escapeHtml(created.screenshot_target_count || 0)}</p>
        <a href="/api/demo-script-pack/packs/${encodeURIComponent(created.pack_id)}/download">Download demo script</a>
      </div>
    ` : `<p class="note">Create a demo script pack after a ready portable release package exists.</p>`}
    ${packs.length ? `
      <div class="workspace-card">
        <h3>Recent script packs</h3>
        ${packs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.pack_id)}</b><br />${escapeHtml(row.pack_readiness || "")}; steps ${escapeHtml(row.script_step_count || 0)}; targets ${escapeHtml(row.screenshot_target_count || 0)}<br /><a href="/api/demo-script-pack/packs/${encodeURIComponent(row.pack_id)}/download">Download script</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderVisualQALedger() {
  const payload = state.visualQALedger;
  const created = state.visualQALedgerCreated;
  if (!payload) {
    els.visualQALedgerStatus.textContent = "No visual QA ledger data loaded.";
    els.visualQALedgerBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const ledgers = payload.ledgers || [];
  els.visualQALedgerStatus.textContent = `${status.screenshot_target_count || 0} targets; ${status.ledger_count || ledgers.length || 0} ledgers; ${status.ready_ledger_count || 0} ready`;
  els.visualQALedgerBody.innerHTML = `
    <div class="workspace-card">
      <h3>Visual QA status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest demo pack:</b> ${escapeHtml(status.latest_demo_pack_id || "")}</p>
      <p><b>Screenshot targets:</b> ${escapeHtml(status.screenshot_target_count || 0)}; <b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created QA ledger</h3>
        <p><b>Ledger:</b> ${escapeHtml(created.ledger_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.ledger_readiness)}</p>
        <p><b>Targets:</b> ${escapeHtml(created.screenshot_target_count || 0)}; <b>Pending:</b> ${escapeHtml(created.pending_capture_count || 0)}</p>
        <a href="/api/visual-qa-snapshot-ledger/ledgers/${encodeURIComponent(created.ledger_id)}/download">Download QA ledger</a>
      </div>
    ` : `<p class="note">Create a visual QA ledger from the latest ready demo script pack.</p>`}
    ${ledgers.length ? `
      <div class="workspace-card">
        <h3>Recent QA ledgers</h3>
        ${ledgers.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.ledger_id)}</b><br />${escapeHtml(row.ledger_readiness || "")}; targets ${escapeHtml(row.screenshot_target_count || 0)}; pending ${escapeHtml(row.pending_capture_count || 0)}<br /><a href="/api/visual-qa-snapshot-ledger/ledgers/${encodeURIComponent(row.ledger_id)}/download">Download ledger</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderVisualBaselineComparison() {
  const payload = state.visualBaselineComparison;
  const created = state.visualBaselineComparisonCreated;
  if (!payload) {
    els.visualBaselineComparisonStatus.textContent = "No visual baseline comparison data loaded.";
    els.visualBaselineComparisonBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const comparisons = payload.comparisons || [];
  els.visualBaselineComparisonStatus.textContent = `${status.ledger_count || 0} ledgers; ${status.comparison_count || comparisons.length || 0} comparisons; ${status.ready_comparison_count || 0} ready`;
  els.visualBaselineComparisonBody.innerHTML = `
    <div class="workspace-card">
      <h3>Baseline comparison status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest ledger:</b> ${escapeHtml(status.latest_ledger_id || "")}</p>
      <p><b>Baseline candidates:</b> ${escapeHtml(status.baseline_candidate_count || 0)}; <b>Targets:</b> ${escapeHtml(status.latest_target_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created baseline comparison</h3>
        <p><b>Comparison:</b> ${escapeHtml(created.comparison_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.comparison_readiness)}</p>
        <p><b>Added:</b> ${escapeHtml((created.target_delta_summary || {}).added_targets || 0)}; <b>Changed:</b> ${escapeHtml((created.target_delta_summary || {}).changed_targets || 0)}; <b>Removed:</b> ${escapeHtml((created.target_delta_summary || {}).removed_targets || 0)}</p>
        <a href="/api/visual-baseline-comparison/comparisons/${encodeURIComponent(created.comparison_id)}/download">Download comparison</a>
      </div>
    ` : `<p class="note">Create a comparison from the two latest Visual QA ledgers.</p>`}
    ${comparisons.length ? `
      <div class="workspace-card">
        <h3>Recent comparisons</h3>
        ${comparisons.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.comparison_id)}</b><br />${escapeHtml(row.comparison_readiness || "")}; added ${escapeHtml(row.added_targets || 0)}; changed ${escapeHtml(row.changed_targets || 0)}; removed ${escapeHtml(row.removed_targets || 0)}<br /><a href="/api/visual-baseline-comparison/comparisons/${encodeURIComponent(row.comparison_id)}/download">Download comparison</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderDemoArtifactCompleteness() {
  const payload = state.demoArtifactCompleteness;
  const created = state.demoArtifactCompletenessCreated;
  if (!payload) {
    els.demoArtifactCompletenessStatus.textContent = "No demo artifact completeness data loaded.";
    els.demoArtifactCompletenessBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const checks = payload.checks || [];
  els.demoArtifactCompletenessStatus.textContent = `${status.complete_required_artifacts || 0}/${status.required_artifact_count || 0} required artifacts complete; ${status.ready_check_count || 0} ready checks`;
  els.demoArtifactCompletenessBody.innerHTML = `
    <div class="workspace-card">
      <h3>Completeness status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Required:</b> ${escapeHtml(status.complete_required_artifacts || 0)} / ${escapeHtml(status.required_artifact_count || 0)}</p>
      <p><b>Missing:</b> ${escapeHtml(status.missing_required_artifacts || 0)}; <b>Invalid:</b> ${escapeHtml(status.invalid_required_artifacts || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created completeness check</h3>
        <p><b>Check:</b> ${escapeHtml(created.check_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.check_readiness)}</p>
        <p><b>Required complete:</b> ${escapeHtml((created.summary || {}).complete_required_artifacts || 0)} / ${escapeHtml((created.summary || {}).required_artifact_count || 0)}</p>
        <a href="/api/demo-artifact-completeness/checks/${encodeURIComponent(created.check_id)}/download">Download completeness report</a>
      </div>
    ` : `<p class="note">Create a final completeness check before sharing the portfolio demo.</p>`}
    ${checks.length ? `
      <div class="workspace-card">
        <h3>Recent completeness checks</h3>
        ${checks.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.check_id)}</b><br />${escapeHtml(row.check_readiness || "")}; missing ${escapeHtml(row.missing_required_artifacts || 0)}; invalid ${escapeHtml(row.invalid_required_artifacts || 0)}<br /><a href="/api/demo-artifact-completeness/checks/${encodeURIComponent(row.check_id)}/download">Download report</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderVisualEvidenceCapture() {
  const payload = state.visualEvidenceCapture;
  const created = state.visualEvidenceCaptureCreated;
  if (!payload) {
    els.visualEvidenceCaptureStatus.textContent = "No visual evidence capture data loaded.";
    els.visualEvidenceCaptureBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const captures = payload.captures || [];
  els.visualEvidenceCaptureStatus.textContent = `${status.ready_capture_count || 0} ready captures; browser ${status.browser_available ? "available" : "missing"}`;
  els.visualEvidenceCaptureBody.innerHTML = `
    <div class="workspace-card">
      <h3>Capture status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Browser:</b> ${escapeHtml(status.browser_path || "")}</p>
      <p><b>Latest ledger:</b> ${escapeHtml(status.latest_ledger_id || "")}</p>
      <p><b>Targets:</b> ${escapeHtml(status.target_count || 0)}; <b>Latest captured:</b> ${escapeHtml(status.latest_captured_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created visual capture</h3>
        <p><b>Capture:</b> ${escapeHtml(created.capture_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.capture_readiness)}</p>
        <p><b>Captured:</b> ${escapeHtml(created.captured_count || 0)} / ${escapeHtml(created.target_count || 0)}; <b>Failed:</b> ${escapeHtml(created.failed_count || 0)}</p>
        <a href="/api/visual-evidence-capture/captures/${encodeURIComponent(created.capture_id)}/download">Download contact sheet</a>
      </div>
    ` : `<p class="note">Capture browser screenshots for the latest Visual QA ledger targets.</p>`}
    ${captures.length ? `
      <div class="workspace-card">
        <h3>Recent captures</h3>
        ${captures.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.capture_id)}</b><br />${escapeHtml(row.capture_readiness || "")}; captured ${escapeHtml(row.captured_count || 0)} / ${escapeHtml(row.target_count || 0)}; failed ${escapeHtml(row.failed_count || 0)}<br /><a href="/api/visual-evidence-capture/captures/${encodeURIComponent(row.capture_id)}/download">Download contact sheet</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderVisualEvidenceReviewDiff() {
  const payload = state.visualEvidenceReviewDiff;
  const created = state.visualEvidenceReviewDiffCreated;
  if (!payload) {
    els.visualEvidenceReviewDiffStatus.textContent = "No visual evidence review diff data loaded.";
    els.visualEvidenceReviewDiffBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const diffs = payload.diffs || [];
  els.visualEvidenceReviewDiffStatus.textContent = `${status.ready_diff_count || 0} ready diffs; ${status.capture_count || 0} ready captures`;
  els.visualEvidenceReviewDiffBody.innerHTML = `
    <div class="workspace-card">
      <h3>Review diff status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest capture:</b> ${escapeHtml(status.latest_capture_id || "")}</p>
      <p><b>Baseline candidates:</b> ${escapeHtml(status.baseline_candidate_count || 0)}</p>
      <p><b>Latest changed screenshots:</b> ${escapeHtml(status.latest_changed_screenshots || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created review diff</h3>
        <p><b>Diff:</b> ${escapeHtml(created.diff_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.diff_readiness)}</p>
        <p><b>Changed screenshots:</b> ${escapeHtml(created.changed_screenshots || 0)}; <b>Metadata changes:</b> ${escapeHtml((created.diff_summary || {}).metadata_changed_targets || 0)}</p>
        <a href="/api/visual-evidence-review-diff/diffs/${encodeURIComponent(created.diff_id)}/download">Download review HTML</a>
      </div>
    ` : `<p class="note">Compare two ready visual evidence captures and review changed screenshot targets.</p>`}
    ${diffs.length ? `
      <div class="workspace-card">
        <h3>Recent review diffs</h3>
        ${diffs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.diff_id)}</b><br />${escapeHtml(row.diff_readiness || "")}; changed ${escapeHtml(row.changed_screenshots || 0)}; added ${escapeHtml(row.added_targets || 0)}; removed ${escapeHtml(row.removed_targets || 0)}<br /><a href="/api/visual-evidence-review-diff/diffs/${encodeURIComponent(row.diff_id)}/download">Download review HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderVisualEvidenceReviewAnnotations() {
  const payload = state.visualEvidenceReviewAnnotations;
  const created = state.visualEvidenceReviewAnnotationsCreated;
  if (!payload) {
    els.visualEvidenceReviewAnnotationsStatus.textContent = "No visual evidence review annotation data loaded.";
    els.visualEvidenceReviewAnnotationsBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const annotations = payload.annotations || [];
  els.visualEvidenceReviewAnnotationsStatus.textContent = `${status.ready_annotation_count || 0} ready annotation sets; ${status.ready_diff_count || 0} ready diffs`;
  els.visualEvidenceReviewAnnotationsBody.innerHTML = `
    <div class="workspace-card">
      <h3>Annotation status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest diff:</b> ${escapeHtml(status.latest_diff_id || "")}</p>
      <p><b>Latest annotation:</b> ${escapeHtml(status.latest_annotation_id || "")}</p>
      <p><b>Pending review targets:</b> ${escapeHtml(status.latest_pending_review_count || 0)}</p>
      <p><b>Expected API endpoints:</b> ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created annotations</h3>
        <p><b>Annotation:</b> ${escapeHtml(created.annotation_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.annotation_readiness)}</p>
        <p><b>Targets:</b> ${escapeHtml(created.target_count || 0)}; <b>Needs review:</b> ${escapeHtml(created.needs_reviewer_attention || 0)}</p>
        <a href="/api/visual-evidence-review-annotations/annotations/${encodeURIComponent(created.annotation_id)}/download">Download annotation HTML</a>
      </div>
    ` : `<p class="note">Create reviewer annotation notes from the latest ready visual evidence review diff.</p>`}
    ${annotations.length ? `
      <div class="workspace-card">
        <h3>Recent annotation sets</h3>
        ${annotations.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.annotation_id)}</b><br />${escapeHtml(row.annotation_readiness || "")}; targets ${escapeHtml(row.target_count || 0)}; needs review ${escapeHtml(row.needs_reviewer_attention || 0)}<br /><a href="/api/visual-evidence-review-annotations/annotations/${encodeURIComponent(row.annotation_id)}/download">Download annotation HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}


function renderVisualEvidenceSignoffPacket() {
  const payload = state.visualEvidenceSignoffPacket;
  const created = state.visualEvidenceSignoffPacketCreated;
  if (!payload) {
    els.visualEvidenceSignoffPacketStatus.textContent = "No visual evidence sign-off packet data loaded.";
    els.visualEvidenceSignoffPacketBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const packets = payload.packets || [];
  els.visualEvidenceSignoffPacketStatus.textContent = `${status.ready_packet_count || 0} ready sign-off packets; ${status.ready_annotation_count || 0} ready annotation sets`;
  els.visualEvidenceSignoffPacketBody.innerHTML = `
    <div class="workspace-card">
      <h3>Sign-off status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest packet:</b> ${escapeHtml(status.latest_packet_id || "")}</p>
      <p><b>Latest annotation:</b> ${escapeHtml(status.latest_annotation_id || "")}</p>
      <p><b>Sign-off status:</b> ${escapeHtml(status.latest_signoff_status || "")}</p>
      <p><b>Reviewer attention:</b> ${escapeHtml(status.latest_attention_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created sign-off packet</h3>
        <p><b>Packet:</b> ${escapeHtml(created.packet_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.packet_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.signoff_status || "")}</p>
        <p><b>Targets:</b> ${escapeHtml(created.target_count || 0)}; <b>Needs review:</b> ${escapeHtml(created.needs_reviewer_attention || 0)}</p>
        <a href="/api/visual-evidence-signoff-packet/packets/${encodeURIComponent(created.packet_id)}/download">Download sign-off HTML</a>
      </div>
    ` : `<p class="note">Create a final reviewer sign-off packet from the latest ready visual evidence annotation set.</p>`}
    ${packets.length ? `
      <div class="workspace-card">
        <h3>Recent sign-off packets</h3>
        ${packets.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.packet_id)}</b><br />${escapeHtml(row.packet_readiness || "")}; status ${escapeHtml(row.signoff_status || "")}; targets ${escapeHtml(row.target_count || 0)}; needs review ${escapeHtml(row.needs_reviewer_attention || 0)}<br /><a href="/api/visual-evidence-signoff-packet/packets/${encodeURIComponent(row.packet_id)}/download">Download sign-off HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}


function renderFinalReviewerLaunchChecklist() {
  const payload = state.finalReviewerLaunchChecklist;
  const created = state.finalReviewerLaunchChecklistCreated;
  if (!payload) {
    els.finalReviewerLaunchChecklistStatus.textContent = "No final reviewer launch checklist data loaded.";
    els.finalReviewerLaunchChecklistBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const checklists = payload.checklists || [];
  els.finalReviewerLaunchChecklistStatus.textContent = `${status.ready_checklist_count || 0} ready launch checklists; ${status.ready_signoff_packet_count || 0} ready sign-off packets`;
  els.finalReviewerLaunchChecklistBody.innerHTML = `
    <div class="workspace-card">
      <h3>Launch checklist status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest checklist:</b> ${escapeHtml(status.latest_checklist_id || "")}</p>
      <p><b>Latest sign-off packet:</b> ${escapeHtml(status.latest_signoff_packet_id || "")}</p>
      <p><b>Launch status:</b> ${escapeHtml(status.latest_launch_status || "")}</p>
      <p><b>Actions:</b> ${escapeHtml(status.latest_action_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created launch checklist</h3>
        <p><b>Checklist:</b> ${escapeHtml(created.checklist_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.checklist_readiness)}</p>
        <p><b>Launch status:</b> ${escapeHtml(created.launch_status || "")}</p>
        <p><b>Actions:</b> ${escapeHtml(created.action_count || 0)}; <b>Must-say lines:</b> ${escapeHtml(created.must_say_count || 0)}</p>
        <a href="/api/final-reviewer-launch-checklist/checklists/${encodeURIComponent(created.checklist_id)}/download">Download launch checklist HTML</a>
      </div>
    ` : `<p class="note">Create the final launch checklist from the latest ready visual evidence sign-off packet.</p>`}
    ${checklists.length ? `
      <div class="workspace-card">
        <h3>Recent launch checklists</h3>
        ${checklists.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.checklist_id)}</b><br />${escapeHtml(row.checklist_readiness || "")}; status ${escapeHtml(row.launch_status || "")}; actions ${escapeHtml(row.action_count || 0)}<br /><a href="/api/final-reviewer-launch-checklist/checklists/${encodeURIComponent(row.checklist_id)}/download">Download launch checklist HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRecruiterDemoBrief() {
  const payload = state.recruiterDemoBrief;
  const created = state.recruiterDemoBriefCreated;
  if (!payload) {
    els.recruiterDemoBriefStatus.textContent = "No recruiter-facing demo brief data loaded.";
    els.recruiterDemoBriefBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const briefs = payload.briefs || [];
  els.recruiterDemoBriefStatus.textContent = `${status.ready_brief_count || 0} ready demo briefs; ${status.ready_launch_checklist_count || 0} ready launch checklists`;
  els.recruiterDemoBriefBody.innerHTML = `
    <div class="workspace-card">
      <h3>Demo brief status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest brief:</b> ${escapeHtml(status.latest_brief_id || "")}</p>
      <p><b>Latest checklist:</b> ${escapeHtml(status.latest_launch_checklist_id || "")}</p>
      <p><b>Brief status:</b> ${escapeHtml(status.latest_brief_status || "")}</p>
      <p><b>Sections:</b> ${escapeHtml(status.latest_section_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created demo brief</h3>
        <p><b>Brief:</b> ${escapeHtml(created.brief_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.brief_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.brief_status || "")}</p>
        <p><b>Sections:</b> ${escapeHtml(created.section_count || 0)}; <b>Proof points:</b> ${escapeHtml(created.proof_point_count || 0)}</p>
        <a href="/api/recruiter-demo-brief/briefs/${encodeURIComponent(created.brief_id)}/download">Download demo brief HTML</a>
      </div>
    ` : `<p class="note">Create a recruiter-facing brief from the latest ready final launch checklist.</p>`}
    ${briefs.length ? `
      <div class="workspace-card">
        <h3>Recent demo briefs</h3>
        ${briefs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.brief_id)}</b><br />${escapeHtml(row.brief_readiness || "")}; status ${escapeHtml(row.brief_status || "")}; sections ${escapeHtml(row.section_count || 0)}<br /><a href="/api/recruiter-demo-brief/briefs/${encodeURIComponent(row.brief_id)}/download">Download demo brief HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderPublicPortfolioPackage() {
  const payload = state.publicPortfolioPackage;
  const created = state.publicPortfolioPackageCreated;
  if (!payload) {
    els.publicPortfolioPackageStatus.textContent = "No public portfolio package data loaded.";
    els.publicPortfolioPackageBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const packages = payload.packages || [];
  els.publicPortfolioPackageStatus.textContent = `${status.ready_package_count || 0} ready packages; ${status.ready_recruiter_demo_brief_count || 0} ready demo briefs`;
  els.publicPortfolioPackageBody.innerHTML = `
    <div class="workspace-card">
      <h3>Portfolio package status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest package:</b> ${escapeHtml(status.latest_package_id || "")}</p>
      <p><b>Latest brief:</b> ${escapeHtml(status.latest_recruiter_demo_brief_id || "")}</p>
      <p><b>Package status:</b> ${escapeHtml(status.latest_package_status || "")}</p>
      <p><b>README sections:</b> ${escapeHtml(status.latest_readme_section_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created package</h3>
        <p><b>Package:</b> ${escapeHtml(created.package_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.package_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.package_status || "")}</p>
        <p><b>README sections:</b> ${escapeHtml(created.readme_section_count || 0)}; <b>Interview steps:</b> ${escapeHtml(created.interview_step_count || 0)}</p>
        <a href="/api/public-portfolio-package/packages/${encodeURIComponent(created.package_id)}/download">Download portfolio package HTML</a>
      </div>
    ` : `<p class="note">Create a public package from the latest ready recruiter demo brief.</p>`}
    ${packages.length ? `
      <div class="workspace-card">
        <h3>Recent portfolio packages</h3>
        ${packages.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.package_id)}</b><br />${escapeHtml(row.package_readiness || "")}; status ${escapeHtml(row.package_status || "")}; sections ${escapeHtml(row.readme_section_count || 0)}<br /><a href="/api/public-portfolio-package/packages/${encodeURIComponent(row.package_id)}/download">Download portfolio package HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderDemoReviewPlaybook() {
  const payload = state.demoReviewPlaybook;
  const created = state.demoReviewPlaybookCreated;
  if (!payload) {
    els.demoReviewPlaybookStatus.textContent = "No demo review playbook data loaded.";
    els.demoReviewPlaybookBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const playbooks = payload.playbooks || [];
  els.demoReviewPlaybookStatus.textContent = `${status.ready_playbook_count || 0} ready playbooks; ${status.ready_public_portfolio_package_count || 0} ready public packages`;
  els.demoReviewPlaybookBody.innerHTML = `
    <div class="workspace-card">
      <h3>Demo playbook status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest playbook:</b> ${escapeHtml(status.latest_playbook_id || "")}</p>
      <p><b>Latest public package:</b> ${escapeHtml(status.latest_public_portfolio_package_id || "")}</p>
      <p><b>Playbook status:</b> ${escapeHtml(status.latest_playbook_status || "")}</p>
      <p><b>Agenda items:</b> ${escapeHtml(status.latest_demo_agenda_item_count || 0)}; <b>Checklist items:</b> ${escapeHtml(status.latest_checklist_item_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created playbook</h3>
        <p><b>Playbook:</b> ${escapeHtml(created.playbook_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.playbook_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.playbook_status || "")}</p>
        <p><b>Agenda:</b> ${escapeHtml(created.demo_agenda_item_count || 0)}; <b>Checklist:</b> ${escapeHtml(created.sharing_checklist_item_count || 0)}; <b>Questions:</b> ${escapeHtml(created.review_question_count || 0)}</p>
        <a href="/api/demo-review-playbook/playbooks/${encodeURIComponent(created.playbook_id)}/download">Download demo playbook HTML</a>
      </div>
    ` : `<p class="note">Create a demo review playbook from the latest ready public portfolio package.</p>`}
    ${playbooks.length ? `
      <div class="workspace-card">
        <h3>Recent demo playbooks</h3>
        ${playbooks.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.playbook_id)}</b><br />${escapeHtml(row.playbook_readiness || "")}; status ${escapeHtml(row.playbook_status || "")}; checklist ${escapeHtml(row.sharing_checklist_item_count || 0)}<br /><a href="/api/demo-review-playbook/playbooks/${encodeURIComponent(row.playbook_id)}/download">Download demo playbook HTML</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderGithubPublicationBundle() {
  const payload = state.githubPublicationBundle;
  const created = state.githubPublicationBundleCreated;
  if (!payload) {
    els.githubPublicationBundleStatus.textContent = "No GitHub publication bundle data loaded.";
    els.githubPublicationBundleBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const bundles = payload.bundles || [];
  els.githubPublicationBundleStatus.textContent = `${status.ready_bundle_count || 0} ready bundles; ${status.ready_demo_review_playbook_count || 0} ready demo playbooks`;
  els.githubPublicationBundleBody.innerHTML = `
    <div class="workspace-card">
      <h3>Publication bundle status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest bundle:</b> ${escapeHtml(status.latest_bundle_id || "")}</p>
      <p><b>Latest playbook:</b> ${escapeHtml(status.latest_demo_review_playbook_id || "")}</p>
      <p><b>Bundle status:</b> ${escapeHtml(status.latest_bundle_status || "")}</p>
      <p><b>README sections:</b> ${escapeHtml(status.latest_readme_section_count || 0)}; <b>Repo files:</b> ${escapeHtml(status.latest_repo_file_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Output:</b> ${escapeHtml(status.output_dir || "")}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created publication bundle</h3>
        <p><b>Bundle:</b> ${escapeHtml(created.bundle_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.bundle_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.bundle_status || "")}</p>
        <p><b>README:</b> ${escapeHtml(created.readme_section_count || 0)}; <b>Repo files:</b> ${escapeHtml(created.repo_file_count || 0)}; <b>Checklist:</b> ${escapeHtml(created.publication_checklist_item_count || 0)}</p>
        <a href="/api/github-publication-bundle/bundles/${encodeURIComponent(created.bundle_id)}/download">Download publication ZIP</a>
      </div>
    ` : `<p class="note">Create a GitHub-ready bundle from the latest ready demo review playbook.</p>`}
    ${bundles.length ? `
      <div class="workspace-card">
        <h3>Recent publication bundles</h3>
        ${bundles.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.bundle_id)}</b><br />${escapeHtml(row.bundle_readiness || "")}; status ${escapeHtml(row.bundle_status || "")}; ZIP ${escapeHtml(row.zip_size_bytes || 0)} bytes<br /><a href="/api/github-publication-bundle/bundles/${encodeURIComponent(row.bundle_id)}/download">Download publication ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRepositoryPublicationQa() {
  const payload = state.repositoryPublicationQa;
  const created = state.repositoryPublicationQaCreated;
  if (!payload) {
    els.repositoryPublicationQaStatus.textContent = "No repository publication QA data loaded.";
    els.repositoryPublicationQaBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const reviews = payload.reviews || [];
  els.repositoryPublicationQaStatus.textContent = `${status.ready_review_count || 0} ready QA reviews; ${status.ready_github_publication_bundle_count || 0} ready publication bundles`;
  els.repositoryPublicationQaBody.innerHTML = `
    <div class="workspace-card">
      <h3>Repository QA status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest review:</b> ${escapeHtml(status.latest_review_id || "")}</p>
      <p><b>Latest bundle:</b> ${escapeHtml(status.latest_github_publication_bundle_id || "")}</p>
      <p><b>Review status:</b> ${escapeHtml(status.latest_review_status || "")}</p>
      <p><b>Required checks:</b> ${escapeHtml(status.latest_required_check_count || 0)}; <b>failed required:</b> ${escapeHtml(status.latest_failed_required_check_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created repository QA</h3>
        <p><b>Review:</b> ${escapeHtml(created.review_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.qa_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.qa_status || "")}</p>
        <p><b>Walkthrough:</b> ${escapeHtml(created.walkthrough_step_count || 0)} steps; <b>failed required:</b> ${escapeHtml(created.failed_required_check_count || 0)}</p>
        <a href="/api/repository-publication-qa/reviews/${encodeURIComponent(created.review_id)}/download">Download repository QA ZIP</a>
      </div>
    ` : `<p class="note">Create a repository QA review from the latest ready GitHub publication bundle.</p>`}
    ${reviews.length ? `
      <div class="workspace-card">
        <h3>Recent repository QA reviews</h3>
        ${reviews.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.review_id)}</b><br />${escapeHtml(row.qa_readiness || "")}; status ${escapeHtml(row.qa_status || "")}; failed required ${escapeHtml(row.failed_required_check_count || 0)}<br /><a href="/api/repository-publication-qa/reviews/${encodeURIComponent(row.review_id)}/download">Download repository QA ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRepositoryExportHandoff() {
  const payload = state.repositoryExportHandoff;
  const created = state.repositoryExportHandoffCreated;
  if (!payload) {
    els.repositoryExportHandoffStatus.textContent = "No repository export handoff data loaded.";
    els.repositoryExportHandoffBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const handoffs = payload.handoffs || [];
  els.repositoryExportHandoffStatus.textContent = `${status.ready_handoff_count || 0} ready handoffs; ${status.ready_repository_qa_count || 0} ready QA reviews`;
  els.repositoryExportHandoffBody.innerHTML = `
    <div class="workspace-card">
      <h3>Repository handoff status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest handoff:</b> ${escapeHtml(status.latest_handoff_id || "")}</p>
      <p><b>Latest QA:</b> ${escapeHtml(status.latest_repository_qa_id || "")}</p>
      <p><b>Handoff status:</b> ${escapeHtml(status.latest_handoff_status || "")}</p>
      <p><b>Include files:</b> ${escapeHtml(status.latest_include_file_count || 0)}; <b>exclude rules:</b> ${escapeHtml(status.latest_exclude_file_count || 0)}</p>
      <p><b>Screenshots:</b> ${escapeHtml(status.latest_screenshot_reference_count || 0)}; <b>license items:</b> ${escapeHtml(status.latest_license_decision_item_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created repository handoff</h3>
        <p><b>Handoff:</b> ${escapeHtml(created.handoff_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.handoff_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.handoff_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>screenshots:</b> ${escapeHtml(created.screenshot_reference_count || 0)}; <b>license:</b> ${escapeHtml(created.license_decision_item_count || 0)}</p>
        <a href="/api/repository-export-handoff/handoffs/${encodeURIComponent(created.handoff_id)}/download">Download repository handoff ZIP</a>
      </div>
    ` : `<p class="note">Create a repository export handoff from the latest ready repository QA review.</p>`}
    ${handoffs.length ? `
      <div class="workspace-card">
        <h3>Recent repository handoffs</h3>
        ${handoffs.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.handoff_id)}</b><br />${escapeHtml(row.handoff_readiness || "")}; status ${escapeHtml(row.handoff_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}<br /><a href="/api/repository-export-handoff/handoffs/${encodeURIComponent(row.handoff_id)}/download">Download handoff ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRepositoryDryRunReview() {
  const payload = state.repositoryDryRunReview;
  const created = state.repositoryDryRunReviewCreated;
  if (!payload) {
    els.repositoryDryRunReviewStatus.textContent = "No repository dry-run review data loaded.";
    els.repositoryDryRunReviewBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const reviews = payload.reviews || [];
  els.repositoryDryRunReviewStatus.textContent = `${status.ready_review_count || 0} ready reviews; ${status.ready_handoff_count || 0} ready handoffs`;
  els.repositoryDryRunReviewBody.innerHTML = `
    <div class="workspace-card">
      <h3>Repository dry-run status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest review:</b> ${escapeHtml(status.latest_review_id || "")}</p>
      <p><b>Latest handoff:</b> ${escapeHtml(status.latest_handoff_id || "")}</p>
      <p><b>Status:</b> ${escapeHtml(status.latest_review_status || "")}</p>
      <p><b>Archive files:</b> ${escapeHtml(status.latest_archive_file_count || 0)}; <b>checklist items:</b> ${escapeHtml(status.latest_final_checklist_item_count || 0)}</p>
      <p><b>Required failed:</b> ${escapeHtml(status.latest_required_failed_count || 0)}; <b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created dry-run review</h3>
        <p><b>Review:</b> ${escapeHtml(created.review_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.review_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.review_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>archive files:</b> ${escapeHtml(created.archive_file_count || 0)}; <b>checklist:</b> ${escapeHtml(created.final_checklist_item_count || 0)}</p>
        <a href="/api/repository-dry-run-review/reviews/${encodeURIComponent(created.review_id)}/download">Download dry-run ZIP</a>
      </div>
    ` : `<p class="note">Create a repository dry-run review from the latest ready repository export handoff.</p>`}
    ${reviews.length ? `
      <div class="workspace-card">
        <h3>Recent dry-run reviews</h3>
        ${reviews.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.review_id)}</b><br />${escapeHtml(row.review_readiness || "")}; status ${escapeHtml(row.review_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}<br /><a href="/api/repository-dry-run-review/reviews/${encodeURIComponent(row.review_id)}/download">Download dry-run ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRepositoryFinalPackageReview() {
  const payload = state.repositoryFinalPackageReview;
  const created = state.repositoryFinalPackageReviewCreated;
  if (!payload) {
    els.repositoryFinalPackageReviewStatus.textContent = "No repository final package review data loaded.";
    els.repositoryFinalPackageReviewBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const reviews = payload.reviews || [];
  els.repositoryFinalPackageReviewStatus.textContent = `${status.ready_review_count || 0} ready final reviews; ${status.ready_dry_run_review_count || 0} ready dry-runs`;
  els.repositoryFinalPackageReviewBody.innerHTML = `
    <div class="workspace-card">
      <h3>Final package review status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest review:</b> ${escapeHtml(status.latest_review_id || "")}</p>
      <p><b>Latest dry-run:</b> ${escapeHtml(status.latest_dry_run_review_id || "")}</p>
      <p><b>Status:</b> ${escapeHtml(status.latest_review_status || "")}</p>
      <p><b>Required failed:</b> ${escapeHtml(status.latest_required_failed_count || 0)}; <b>public path issues:</b> ${escapeHtml(status.latest_public_path_issue_count || 0)}</p>
      <p><b>Redacted paths:</b> ${escapeHtml(status.latest_redacted_path_count || 0)}; <b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created final package review</h3>
        <p><b>Review:</b> ${escapeHtml(created.review_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.review_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.review_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>public path issues:</b> ${escapeHtml(created.public_path_issue_count || 0)}; <b>redacted paths:</b> ${escapeHtml(created.redacted_path_count || 0)}</p>
        <a href="/api/repository-final-package-review/reviews/${encodeURIComponent(created.review_id)}/download">Download final package ZIP</a>
      </div>
    ` : `<p class="note">Create a final repository package review from the latest ready dry-run review.</p>`}
    ${reviews.length ? `
      <div class="workspace-card">
        <h3>Recent final package reviews</h3>
        ${reviews.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.review_id)}</b><br />${escapeHtml(row.review_readiness || "")}; status ${escapeHtml(row.review_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}; public path issues ${escapeHtml(row.public_path_issue_count || 0)}<br /><a href="/api/repository-final-package-review/reviews/${encodeURIComponent(row.review_id)}/download">Download final package ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderPublicReadmeCleanupReview() {
  const payload = state.publicReadmeCleanupReview;
  const created = state.publicReadmeCleanupReviewCreated;
  if (!payload) {
    els.publicReadmeCleanupReviewStatus.textContent = "No public README cleanup review data loaded.";
    els.publicReadmeCleanupReviewBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const reviews = payload.reviews || [];
  els.publicReadmeCleanupReviewStatus.textContent = `${status.ready_review_count || 0} ready cleanup reviews; ${status.ready_final_package_review_count || 0} ready final package reviews`;
  els.publicReadmeCleanupReviewBody.innerHTML = `
    <div class="workspace-card">
      <h3>Public README cleanup status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest review:</b> ${escapeHtml(status.latest_review_id || "")}</p>
      <p><b>Latest final package:</b> ${escapeHtml(status.latest_final_package_review_id || "")}</p>
      <p><b>Status:</b> ${escapeHtml(status.latest_review_status || "")}</p>
      <p><b>Required failed:</b> ${escapeHtml(status.latest_required_failed_count || 0)}; <b>README issues:</b> ${escapeHtml(status.latest_public_readme_issue_count || 0)}</p>
      <p><b>Screenshots:</b> ${escapeHtml(status.latest_screenshot_evidence_count || 0)}; <b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created public README cleanup review</h3>
        <p><b>Review:</b> ${escapeHtml(created.review_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.review_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.review_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>README issues:</b> ${escapeHtml(created.public_readme_issue_count || 0)}; <b>screenshots:</b> ${escapeHtml(created.screenshot_evidence_count || 0)}</p>
        <a href="/api/public-readme-cleanup-review/reviews/${encodeURIComponent(created.review_id)}/download">Download cleanup ZIP</a>
      </div>
    ` : `<p class="note">Create a public README cleanup review from the latest ready final package review.</p>`}
    ${reviews.length ? `
      <div class="workspace-card">
        <h3>Recent README cleanup reviews</h3>
        ${reviews.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.review_id)}</b><br />${escapeHtml(row.review_readiness || "")}; status ${escapeHtml(row.review_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}; README issues ${escapeHtml(row.public_readme_issue_count || 0)}<br /><a href="/api/public-readme-cleanup-review/reviews/${encodeURIComponent(row.review_id)}/download">Download cleanup ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderPublicRepositoryPolishPackage() {
  const payload = state.publicRepositoryPolishPackage;
  const created = state.publicRepositoryPolishPackageCreated;
  if (!payload) {
    els.publicRepositoryPolishPackageStatus.textContent = "No public repository polish package data loaded.";
    els.publicRepositoryPolishPackageBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const packages = payload.packages || [];
  els.publicRepositoryPolishPackageStatus.textContent = `${status.ready_package_count || 0} ready polish packages; ${status.ready_cleanup_review_count || 0} ready cleanup reviews`;
  els.publicRepositoryPolishPackageBody.innerHTML = `
    <div class="workspace-card">
      <h3>Public repository polish status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest package:</b> ${escapeHtml(status.latest_package_id || "")}</p>
      <p><b>Latest cleanup review:</b> ${escapeHtml(status.latest_cleanup_review_id || "")}</p>
      <p><b>Status:</b> ${escapeHtml(status.latest_package_status || "")}</p>
      <p><b>Required failed:</b> ${escapeHtml(status.latest_required_failed_count || 0)}; <b>README issues:</b> ${escapeHtml(status.latest_public_readme_issue_count || 0)}</p>
      <p><b>Screenshots:</b> ${escapeHtml(status.latest_screenshot_target_count || 0)}; <b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created public repository polish package</h3>
        <p><b>Package:</b> ${escapeHtml(created.package_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.package_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.package_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>README issues:</b> ${escapeHtml(created.public_readme_issue_count || 0)}; <b>screenshots:</b> ${escapeHtml(created.screenshot_target_count || 0)}</p>
        <a href="/api/public-repository-polish-package/packages/${encodeURIComponent(created.package_id)}/download">Download polish ZIP</a>
      </div>
    ` : `<p class="note">Create a polish package from the latest ready public README cleanup review.</p>`}
    ${packages.length ? `
      <div class="workspace-card">
        <h3>Recent polish packages</h3>
        ${packages.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.package_id)}</b><br />${escapeHtml(row.package_readiness || "")}; status ${escapeHtml(row.package_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}; README issues ${escapeHtml(row.public_readme_issue_count || 0)}<br /><a href="/api/public-repository-polish-package/packages/${encodeURIComponent(row.package_id)}/download">Download polish ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderRepositoryExportChecklist() {
  const payload = state.repositoryExportChecklist;
  const created = state.repositoryExportChecklistCreated;
  if (!payload) {
    els.repositoryExportChecklistStatus.textContent = "No repository export checklist data loaded.";
    els.repositoryExportChecklistBody.innerHTML = "";
    return;
  }
  const status = payload.status || {};
  const checklists = payload.checklists || [];
  els.repositoryExportChecklistStatus.textContent = `${status.ready_checklist_count || 0} ready export checklists; ${status.ready_polish_package_count || 0} ready polish packages`;
  els.repositoryExportChecklistBody.innerHTML = `
    <div class="workspace-card">
      <h3>Repository export checklist status</h3>
      <p><b>Readiness:</b> ${escapeHtml(status.readiness_level || "")}</p>
      <p><b>Latest checklist:</b> ${escapeHtml(status.latest_checklist_id || "")}</p>
      <p><b>Latest polish package:</b> ${escapeHtml(status.latest_polish_package_id || "")}</p>
      <p><b>Status:</b> ${escapeHtml(status.latest_checklist_status || "")}</p>
      <p><b>Required failed:</b> ${escapeHtml(status.latest_required_failed_count || 0)}; <b>screenshots:</b> ${escapeHtml(status.latest_screenshot_evidence_count || 0)} / ${escapeHtml(status.latest_screenshot_target_count || 0)}</p>
      <p><b>API endpoints:</b> ${escapeHtml(status.checked_api_endpoints || 0)} / ${escapeHtml(status.expected_api_endpoints || "")}</p>
      <p><b>Source GIS included:</b> ${escapeHtml(String(status.includes_source_gis))}</p>
    </div>
    ${created ? `
      <div class="workspace-card">
        <h3>Created repository export checklist</h3>
        <p><b>Checklist:</b> ${escapeHtml(created.checklist_id)}</p>
        <p><b>Readiness:</b> ${escapeHtml(created.checklist_readiness)}</p>
        <p><b>Status:</b> ${escapeHtml(created.checklist_status || "")}</p>
        <p><b>Required failed:</b> ${escapeHtml(created.required_failed_count || 0)}; <b>screenshots:</b> ${escapeHtml(created.screenshot_evidence_count || 0)} / ${escapeHtml(created.screenshot_target_count || 0)}</p>
        <a href="/api/repository-export-checklist/checklists/${encodeURIComponent(created.checklist_id)}/download">Download export checklist ZIP</a>
      </div>
    ` : `<p class="note">Create an export checklist from the latest ready public repository polish package.</p>`}
    ${checklists.length ? `
      <div class="workspace-card">
        <h3>Recent export checklists</h3>
        ${checklists.slice(0, 3).map((row) => `<p><b>${escapeHtml(row.checklist_id)}</b><br />${escapeHtml(row.checklist_readiness || "")}; status ${escapeHtml(row.checklist_status || "")}; failed required ${escapeHtml(row.required_failed_count || 0)}; screenshots ${escapeHtml(row.screenshot_evidence_count || 0)} / ${escapeHtml(row.screenshot_target_count || 0)}<br /><a href="/api/repository-export-checklist/checklists/${encodeURIComponent(row.checklist_id)}/download">Download export checklist ZIP</a></p>`).join("")}
      </div>
    ` : ""}
  `;
}

function renderAnalysisProfiles() {
  const payload = state.analysisProfiles;
  if (!payload || payload.error) {
    els.analysisProfilesStatus.textContent = payload && payload.error ? `Profiles failed: ${payload.error}` : "No profiles loaded.";
    els.analysisProfilesBody.innerHTML = `<p class="note">Analysis profiles are not available.</p>`;
    return;
  }
  const profiles = payload.profiles || [];
  const runnable = profiles.filter((profile) => profile.can_run).length;
  els.analysisProfilesStatus.textContent = `${profiles.length} profiles; ${runnable} ready to run`;
  els.analysisProfilesBody.innerHTML = profiles
    .map((profile) => {
      const blockers = profile.blockers || [];
      return `
        <div class="workspace-card">
          <h3>${escapeHtml(profile.name)}</h3>
          <p><b>Status:</b> ${escapeHtml(profile.status)}; <b>Runner:</b> ${escapeHtml(profile.runner_status)}</p>
          <p><b>Readiness:</b> ${escapeHtml(profile.readiness_level || "")}</p>
          <p><b>Can plan:</b> ${profile.can_plan ? "yes" : "no"}; <b>Can run:</b> ${profile.can_run ? "yes" : "no"}</p>
          <p><b>Outputs:</b> ${escapeHtml((profile.outputs || []).slice(0, 3).join(", "))}</p>
          ${blockers.length ? `<p><b>Blockers:</b> ${escapeHtml(blockers.slice(0, 3).join(", "))}</p>` : `<p><b>Blockers:</b> none</p>`}
        </div>
      `;
    })
    .join("");
}

function renderProfileWorkspaces() {
  if (!state.profileWorkspaces.length) {
    els.profileRunnerStatus.textContent = "No profile workspaces yet.";
    els.profileWorkspacesBody.innerHTML = `<p class="note">Run a profile to create a profile-specific output workspace.</p>`;
    return;
  }
  els.profileRunnerStatus.textContent = `${state.profileWorkspaces.length} profile workspace outputs`;
  els.profileWorkspacesBody.innerHTML = state.profileWorkspaces
    .map((workspace) => {
      const isPark = workspace.profile_id === "park_playground_access";
      const isOsm = workspace.profile_id === "osm_tag_quality";
      const outputId = isOsm ? "tag_quality_summary" : isPark ? "park_playground_access_results" : "transit_stop_access_results";
      const countLabel = isOsm ? "Tag rows" : isPark ? "Public spaces" : "Transit stops";
      const countValue = isOsm ? workspace.tag_count_rows : isPark ? workspace.public_spaces : workspace.transit_stops;
      return `
        <div class="workspace-card">
          <h3>${escapeHtml(workspace.profile_id)}</h3>
          <p><b>Workspace:</b> ${escapeHtml(workspace.workspace_id)}</p>
          <p><b>Base:</b> ${escapeHtml(workspace.base_workspace_id || "")}</p>
          <p><b>${countLabel}:</b> ${countValue ?? ""}; <b>Tables:</b> ${workspace.table_count}</p>
          <a href="/api/profile-workspaces/${encodeURIComponent(workspace.workspace_id)}/download/${outputId}">Download results</a>
        </div>
      `;
    })
    .join("");
}

async function runTransitProfile() {
  const baseWorkspaceId = state.activeWorkspaceId || DEFAULT_DASHBOARD_WORKSPACE_ID;
  els.profileRunnerStatus.textContent = "Running transit stop walk-access profile...";
  const result = await postJson("/api/profile-runners/transit_stop_walk_access/run", {
    base_workspace_id: baseWorkspaceId,
    workspace_id: "transit_stop_walk_access_kfar_saba_v001",
  });
  if (!result.ok) {
    els.profileRunnerStatus.textContent = `Transit profile failed: ${result.error || "unknown error"}`;
    return;
  }
  const counts = result.workspace && result.workspace.summary && result.workspace.summary.counts;
  els.profileRunnerStatus.textContent = `Transit profile ready: ${counts ? counts.transit_stops : ""} stops`;
  await loadProfileWorkspaces();
  await loadAnalysisProfiles();
}

async function runParkProfile() {
  const baseWorkspaceId = state.activeWorkspaceId || DEFAULT_DASHBOARD_WORKSPACE_ID;
  els.profileRunnerStatus.textContent = "Running park and playground access profile...";
  const result = await postJson("/api/profile-runners/park_playground_access/run", {
    base_workspace_id: baseWorkspaceId,
    workspace_id: DEFAULT_PARK_PROFILE_WORKSPACE_ID,
  });
  if (!result.ok) {
    els.profileRunnerStatus.textContent = `Park profile failed: ${result.error || "unknown error"}`;
    return;
  }
  const counts = result.workspace && result.workspace.summary && result.workspace.summary.counts;
  els.profileRunnerStatus.textContent = `Park profile ready: ${counts ? counts.public_spaces : ""} public spaces`;
  await loadProfileWorkspaces();
  await loadAnalysisProfiles();
}

function renderAnalysisRuns() {
  if (!state.analysisRuns.length) {
    els.analysisRunsStatus.textContent = "No analysis runs yet.";
    els.analysisRunsBody.innerHTML = `<p class="note">Create an analysis to populate this list.</p>`;
    return;
  }
  els.analysisRunsStatus.textContent = `${state.analysisRuns.length} analysis runs`;
  els.analysisRunsBody.innerHTML = state.analysisRuns
    .map((run) => `
      <div class="workspace-card">
        <h3>${escapeHtml(run.status)} - ${escapeHtml(run.run_type)}</h3>
        <p><b>Run:</b> ${escapeHtml(run.run_id)}</p>
        <p><b>Pilot:</b> ${escapeHtml(run.pilot_name || run.pilot_osm_id || "")}</p>
        <p><b>Workspace:</b> ${escapeHtml(run.active_workspace_id || "")}</p>
        <p><b>Outputs:</b> ${run.output_count}; <b>Runtime:</b> ${run.runtime_seconds ?? ""}</p>
        <button type="button" data-open-run="${escapeHtml(run.run_id)}">Open dashboard</button>
        <button type="button" data-rerun="${escapeHtml(run.run_id)}">Rerun</button>
      </div>
    `)
    .join("");
  [...els.analysisRunsBody.querySelectorAll("[data-open-run]")].forEach((button) => {
    button.addEventListener("click", () => openAnalysisRun(button.dataset.openRun));
  });
  [...els.analysisRunsBody.querySelectorAll("[data-rerun]")].forEach((button) => {
    button.addEventListener("click", () => rerunAnalysisRun(button.dataset.rerun));
  });
}

async function openAnalysisRun(runId) {
  const detail = await getJson(`/api/analysis-runs/${encodeURIComponent(runId)}`);
  if (!detail.ok) {
    els.analysisRunsStatus.textContent = `Run load failed: ${detail.error || "unknown error"}`;
    return;
  }
  const workspaceId = detail.run.active_workspace_id;
  if (workspaceId) {
    state.activeWorkspaceId = workspaceId;
    await loadWorkspaceRegistry();
    await loadDashboardWorkspace();
  }
  const outputLinks = detail.outputs.slice(0, 4)
    .map((output) => `<a href="${escapeHtml(output.download_url)}">${escapeHtml(output.label)}</a>`)
    .join(" ");
  els.analysisRunsStatus.innerHTML = `Opened ${escapeHtml(runId)} ${outputLinks}`;
}

async function rerunAnalysisRun(runId) {
  els.analysisRunsStatus.textContent = `Rerunning ${runId}...`;
  const result = await postJson(`/api/analysis-runs/${encodeURIComponent(runId)}/rerun`, {});
  if (!result.ok) {
    els.analysisRunsStatus.textContent = `Rerun failed: ${result.error || "unknown error"}`;
    return;
  }
  els.analysisRunsStatus.textContent = `Rerun queued: ${result.job.job_id}`;
  await loadJobs();
  await loadAnalysisRuns();
  await pollJob(result.job.job_id);
}

function latestRunIds(limit = 1) {
  return state.analysisRuns
    .filter((run) => run.run_id && run.status === "succeeded")
    .slice(0, limit)
    .map((run) => run.run_id);
}

async function generatePortfolioReport() {
  if (!state.analysisRuns.length) await loadAnalysisRuns();
  const [runId] = latestRunIds(1);
  if (!runId) {
    els.portfolioReportsStatus.textContent = "No completed analysis run is available.";
    return;
  }
  els.portfolioReportsStatus.textContent = `Generating report for ${runId}...`;
  const result = await postJson("/api/portfolio-reports/from-run", { run_id: runId });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Report failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Report ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.report_id)}</a>`;
  await loadPortfolioReports();
}

async function generateTransitPortfolioReport() {
  if (!state.profileWorkspaces.length) await loadProfileWorkspaces();
  const transitWorkspace = state.profileWorkspaces.find((workspace) => workspace.workspace_id === DEFAULT_TRANSIT_PROFILE_WORKSPACE_ID)
    || state.profileWorkspaces.find((workspace) => workspace.profile_id === "transit_stop_walk_access");
  const workspaceId = transitWorkspace ? transitWorkspace.workspace_id : DEFAULT_TRANSIT_PROFILE_WORKSPACE_ID;
  els.portfolioReportsStatus.textContent = `Generating transit report for ${workspaceId}...`;
  const result = await postJson("/api/portfolio-reports/from-profile-workspace", { workspace_id: workspaceId });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Transit report failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Transit report ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.report_id)}</a>`;
  await loadPortfolioReports();
}

async function generateParkPortfolioReport() {
  if (!state.profileWorkspaces.length) await loadProfileWorkspaces();
  const parkWorkspace = state.profileWorkspaces.find((workspace) => workspace.workspace_id === DEFAULT_PARK_PROFILE_WORKSPACE_ID)
    || state.profileWorkspaces.find((workspace) => workspace.profile_id === "park_playground_access");
  const workspaceId = parkWorkspace ? parkWorkspace.workspace_id : DEFAULT_PARK_PROFILE_WORKSPACE_ID;
  els.portfolioReportsStatus.textContent = `Generating park report for ${workspaceId}...`;
  const result = await postJson("/api/portfolio-reports/from-profile-workspace", { workspace_id: workspaceId });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Park report failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Park report ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.report_id)}</a>`;
  await loadPortfolioReports();
}

async function generateProfileComparisonReport() {
  els.portfolioReportsStatus.textContent = "Generating profile comparison report...";
  const result = await postJson("/api/portfolio-reports/profile-comparison", {
    base_workspace_id: state.activeWorkspaceId || DEFAULT_DASHBOARD_WORKSPACE_ID,
    profile_workspace_ids: [DEFAULT_TRANSIT_PROFILE_WORKSPACE_ID, DEFAULT_PARK_PROFILE_WORKSPACE_ID],
  });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Profile comparison failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Profile comparison ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.report_id)}</a>`;
  await loadProfileWorkspaces();
  await loadPortfolioReports();
}

async function generateProfileExportBundle() {
  els.portfolioReportsStatus.textContent = "Generating profile dashboard export bundle...";
  const result = await postJson("/api/export-bundles/profile-dashboard", {
    base_workspace_id: state.activeWorkspaceId || DEFAULT_DASHBOARD_WORKSPACE_ID,
    profile_workspace_ids: [DEFAULT_TRANSIT_PROFILE_WORKSPACE_ID, DEFAULT_PARK_PROFILE_WORKSPACE_ID],
  });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Bundle failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Profile bundle ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.bundle_id)}</a>`;
  await loadPortfolioReports();
}

async function comparePortfolioRuns() {
  if (!state.analysisRuns.length) await loadAnalysisRuns();
  const runIds = latestRunIds(2);
  if (runIds.length < 2) {
    els.portfolioReportsStatus.textContent = "Need at least two completed analysis runs.";
    return;
  }
  els.portfolioReportsStatus.textContent = "Generating run comparison...";
  const result = await postJson("/api/portfolio-reports/compare", { run_ids: runIds });
  if (!result.ok) {
    els.portfolioReportsStatus.textContent = `Compare failed: ${result.error || "unknown error"}`;
    return;
  }
  els.portfolioReportsStatus.innerHTML = `Compare ready: <a href="${escapeHtml(result.download_url)}">${escapeHtml(result.report_id)}</a>`;
  await loadPortfolioReports();
}

function renderPortfolioReports() {
  const reports = state.portfolioReports || [];
  const bundles = state.exportBundles || [];
  if (!reports.length && !bundles.length) {
    els.portfolioReportsStatus.textContent = "No generated portfolio reports yet.";
    els.portfolioReportsBody.innerHTML = `<p class="note">Generate a report from a completed analysis run or profile dashboard.</p>`;
    return;
  }
  els.portfolioReportsStatus.textContent = `${reports.length} reports; ${bundles.length} bundles`;
  const reportCards = reports
    .map((report) => `
      <div class="workspace-card">
        <h3>${escapeHtml(report.report_type)}</h3>
        <p><b>Report:</b> ${escapeHtml(report.report_id)}</p>
        <p><b>Run/profile:</b> ${escapeHtml(report.run_id || report.profile_id || "multiple")}</p>
        <p><b>Workspace:</b> ${escapeHtml(report.workspace_id || "")}</p>
        <p><b>Created:</b> ${escapeHtml(report.generated_at_utc || "")}</p>
        <a href="${escapeHtml(report.download_url)}">Download Markdown</a>
      </div>
    `)
    .join("");
  const bundleCards = bundles
    .map((bundle) => `
      <div class="workspace-card">
        <h3>${escapeHtml(bundle.bundle_type)}</h3>
        <p><b>Bundle:</b> ${escapeHtml(bundle.bundle_id)}</p>
        <p><b>Profiles:</b> ${bundle.profile_count}; <b>Contract:</b> ${escapeHtml(bundle.profile_dashboard_contract_version || "")}</p>
        <p><b>Comparison:</b> ${escapeHtml(bundle.comparison_report_id || "")}</p>
        <p><b>Created:</b> ${escapeHtml(bundle.generated_at_utc || "")}</p>
        <a href="${escapeHtml(bundle.download_url)}">Download Bundle</a>
      </div>
    `)
    .join("");
  els.portfolioReportsBody.innerHTML = reportCards + bundleCards;
}

function renderWorkspaceRegistry() {
  els.workspaceStatus.textContent = `${state.workspaces.length} registered`;
  if (!state.workspaces.length) {
    els.workspaceRegistry.innerHTML = `<p class="note">No generated workspaces yet.</p>`;
    return;
  }
  els.workspaceRegistry.innerHTML = state.workspaces
    .map((workspace) => `
      <div class="workspace-card">
        <h3>${escapeHtml(workspace.workspace_id)}</h3>
        <p><b>Template:</b> ${escapeHtml(workspace.template_id)}</p>
        <p><b>Source:</b> ${escapeHtml(workspace.source_dataset_id)}</p>
        <p><b>Tables:</b> ${workspace.table_count}</p>
        <p><b>Route-aware:</b> ${workspace.workspace_id.includes("route_aware") ? "yes" : "no"}</p>
        <p><b>Created:</b> ${escapeHtml(workspace.created_at_utc || "")}</p>
      </div>
    `)
    .join("");
}

function renderJobs() {
  if (!state.jobs.length) {
    els.jobHistory.innerHTML = `<p class="note">No background jobs yet.</p>`;
    return;
  }
  els.jobHistory.innerHTML = state.jobs
    .map((job) => `
      <div class="workspace-card">
        <h3>${escapeHtml(job.status)} - ${escapeHtml(job.job_type)}</h3>
        <p><b>Job:</b> ${escapeHtml(job.job_id)}</p>
        <p><b>Pilot:</b> ${escapeHtml(job.pilot_name || job.pilot_osm_id || "")}</p>
        <p><b>Workspace:</b> ${escapeHtml(job.active_workspace_id || "")}</p>
        <p><b>Runtime:</b> ${job.runtime_seconds ?? ""}</p>
        <p><b>Logs:</b> ${job.log_count}</p>
      </div>
    `)
    .join("");
}

async function pollJob(jobId) {
  for (let i = 0; i < 90; i += 1) {
    const job = await getJson(`/api/jobs/${encodeURIComponent(jobId)}`);
    const latestLog = (job.logs || []).at(-1);
    els.jobStatus.textContent = `${job.status}: ${latestLog ? latestLog.message : job.job_id}`;
    if (job.status === "succeeded") {
      const active = job.result && job.result.active_workspace_id;
      if (active) state.activeWorkspaceId = active;
      els.pilotStatus.textContent = `Pilot workspace ready: ${state.activeWorkspaceId}`;
      await loadWorkspaceRegistry();
      await loadDashboardWorkspace();
      await loadJobs();
      await loadAnalysisRuns();
      await loadPortfolioReports();
      return;
    }
    if (job.status === "failed") {
      els.pilotStatus.textContent = `Pilot job failed: ${job.error || "unknown error"}`;
      await loadJobs();
      await loadAnalysisRuns();
      await loadPortfolioReports();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
  els.jobStatus.textContent = `Still running: ${jobId}`;
  await loadJobs();
  await loadPortfolioReports();
}

function renderTable() {
  els.rows.innerHTML = state.candidates
    .map(
      (row) => `
        <tr data-id="${escapeHtml(row.generator_id)}" tabindex="0" role="button" aria-label="Select review candidate ${escapeHtml(row.name || row.generator_id)}" class="${state.selected && state.selected.generator_id === row.generator_id ? "selected-row" : ""}">
          <td>${reviewStatusDot(row.generator_id)}${escapeHtml(row.generator_id)}</td>
          <td>${escapeHtml(typeLabel(row.generator_type))}</td>
          <td>${escapeHtml(row.name || "")}</td>
          <td>${fmt(row.nearest_crossing_m, " m")}</td>
          <td>${fmt(row.nearest_major_road_m, " m")}</td>
          <td><b>${row.route_aware_available ? row.route_review_priority_score : row.risk_score}</b></td>
          <td>${flagPills((row.risk_flags || []).slice(0, 2))}</td>
        </tr>
      `,
    )
    .join("");
  [...els.rows.querySelectorAll("tr")].forEach((tr) => {
    tr.addEventListener("click", () => selectCandidate(tr.dataset.id));
    tr.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCandidate(tr.dataset.id);
      }
    });
  });
}

const MAP_BASE_W = 1000;
const MAP_BASE_H = 640;
let mapDragStart = null;

function mapViewBoxString(view) {
  return `${view.x.toFixed(2)} ${view.y.toFixed(2)} ${view.w.toFixed(2)} ${view.h.toFixed(2)}`;
}

function clampMapView() {
  const view = state.mapView;
  if (!view) return;
  view.w = Math.max(80, Math.min(MAP_BASE_W, view.w));
  view.h = view.w * (MAP_BASE_H / MAP_BASE_W);
  const slackX = MAP_BASE_W * 0.25;
  const slackY = MAP_BASE_H * 0.25;
  view.x = Math.max(-slackX, Math.min(MAP_BASE_W + slackX - view.w, view.x));
  view.y = Math.max(-slackY, Math.min(MAP_BASE_H + slackY - view.h, view.y));
}

function applyMapView() {
  if (!els.map || !state.mapView) return;
  clampMapView();
  els.map.setAttribute("viewBox", mapViewBoxString(state.mapView));
}

function resetMapView() {
  state.mapView = { x: 0, y: 0, w: MAP_BASE_W, h: MAP_BASE_H };
  applyMapView();
}

function svgPointFromEvent(evt) {
  if (!els.map.getScreenCTM) return null;
  const ctm = els.map.getScreenCTM();
  if (!ctm) return null;
  const pt = els.map.createSVGPoint();
  pt.x = evt.clientX;
  pt.y = evt.clientY;
  return pt.matrixTransform(ctm.inverse());
}

function zoomMapBy(factor, focus) {
  if (!state.mapView) resetMapView();
  const view = state.mapView;
  const anchor = focus || { x: view.x + view.w / 2, y: view.y + view.h / 2 };
  const rx = (anchor.x - view.x) / view.w;
  const ry = (anchor.y - view.y) / view.h;
  view.w *= factor;
  view.h = view.w * (MAP_BASE_H / MAP_BASE_W);
  view.x = anchor.x - rx * view.w;
  view.y = anchor.y - ry * view.h;
  applyMapView();
}

function setupMapInteractions() {
  if (!els.map || els.map.dataset.interactive === "1") return;
  els.map.dataset.interactive = "1";

  els.map.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomMapBy(event.deltaY < 0 ? 0.85 : 1 / 0.85, svgPointFromEvent(event));
  }, { passive: false });

  els.map.addEventListener("pointerdown", (event) => {
    if (event.target.classList && event.target.classList.contains("candidate")) return;
    mapDragStart = { x: event.clientX, y: event.clientY };
    els.map.classList.add("grabbing");
    try {
      els.map.setPointerCapture(event.pointerId);
    } catch (err) {
      /* pointer capture is best-effort */
    }
  });

  els.map.addEventListener("pointermove", (event) => {
    if (!mapDragStart || !state.mapView) return;
    const rect = els.map.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    state.mapView.x -= (event.clientX - mapDragStart.x) * (state.mapView.w / rect.width);
    state.mapView.y -= (event.clientY - mapDragStart.y) * (state.mapView.h / rect.height);
    mapDragStart = { x: event.clientX, y: event.clientY };
    applyMapView();
  });

  const endMapDrag = () => {
    mapDragStart = null;
    els.map.classList.remove("grabbing");
  };
  els.map.addEventListener("pointerup", endMapDrag);
  els.map.addEventListener("pointercancel", endMapDrag);
  els.map.addEventListener("pointerleave", endMapDrag);

  const host = els.map.parentElement;
  if (host && !host.querySelector(".map-zoom-controls")) {
    const controls = document.createElement("div");
    controls.className = "map-zoom-controls";
    controls.innerHTML =
      '<button type="button" data-zoom="in" aria-label="Zoom in">+</button>' +
      '<button type="button" data-zoom="out" aria-label="Zoom out">−</button>' +
      '<button type="button" data-zoom="reset" aria-label="Reset map view">⤢</button>';
    controls.addEventListener("click", (event) => {
      const action = event.target.dataset ? event.target.dataset.zoom : "";
      if (action === "in") zoomMapBy(0.8, null);
      else if (action === "out") zoomMapBy(1.25, null);
      else if (action === "reset") resetMapView();
    });
    host.appendChild(controls);
  }
}

// ---- P2: real Leaflet street basemap (product mode only) ----
// In product mode the map becomes a real OSM/CARTO street basemap on #mapCanvas.
// The SVG #map stays as the full-mode renderer AND the offline fallback (when
// tiles are unreachable). Full mode never initialises Leaflet, so the suites'
// full-mode screenshot gate stays entirely off this path.
let leafletMap = null;
let leafletContextLayer = null;
let leafletCandidateLayer = null;
let leafletFitted = false;
let leafletContextDone = false;
let leafletTileFailed = false;

function leafletAvailable() {
  return (
    Boolean(window.L) &&
    Boolean(els.mapCanvas) &&
    document.body.classList.contains("product-mode") &&
    !leafletTileFailed
  );
}

const CATEGORY_SHAPE = {
  road: { color: "#ea580c", shape: "triangle" },
  crossing: { color: "#059669", shape: "square" },
  generator: { color: "#2563eb", shape: "diamond" },
  candidate: { color: "#e11d48", shape: "circle" },
};

function markerSvg(shape, color, size, stroke) {
  const c = (size / 2).toFixed(1);
  const sw = stroke ? `stroke="${stroke}" stroke-width="1.5"` : "";
  let body;
  if (shape === "square") {
    body = `<rect x="1.5" y="1.5" width="${size - 3}" height="${size - 3}" fill="${color}" ${sw}/>`;
  } else if (shape === "triangle") {
    body = `<polygon points="${c},1.5 ${size - 1.5},${size - 1.5} 1.5,${size - 1.5}" fill="${color}" ${sw}/>`;
  } else if (shape === "diamond") {
    body = `<polygon points="${c},1.5 ${size - 1.5},${c} ${c},${size - 1.5} 1.5,${c}" fill="${color}" ${sw}/>`;
  } else {
    body = `<circle cx="${c}" cy="${c}" r="${(size / 2 - 1.5).toFixed(1)}" fill="${color}" ${sw}/>`;
  }
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
}

function categoryIcon(category, size, stroke) {
  const meta = CATEGORY_SHAPE[category];
  return window.L.divIcon({
    html: markerSvg(meta.shape, meta.color, size, stroke),
    className: "gmark",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function ensureLeafletMap() {
  if (leafletMap || !window.L || !els.mapCanvas) return leafletMap;
  leafletMap = window.L.map(els.mapCanvas, { zoomControl: true, attributionControl: true });
  const tiles = window.L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  });
  let tileErrors = 0;
  tiles.on("tileerror", () => {
    tileErrors += 1;
    if (tileErrors >= 4 && !leafletTileFailed) {
      leafletTileFailed = true;
      if (els.mapPanel) els.mapPanel.classList.remove("leaflet-on");
      renderMapSvg();
    }
  });
  tiles.addTo(leafletMap);
  leafletContextLayer = window.L.layerGroup().addTo(leafletMap);
  leafletCandidateLayer = window.L.layerGroup().addTo(leafletMap);
  return leafletMap;
}

function addContextMarkers(points, category, size) {
  for (const p of points) {
    if (!Number.isFinite(p.lon) || !Number.isFinite(p.lat)) continue;
    window.L.marker([p.lat, p.lon], { icon: categoryIcon(category, size, null), interactive: false, keyboard: false }).addTo(
      leafletContextLayer,
    );
  }
}

function renderMapLeaflet() {
  // Make #mapCanvas visible BEFORE initialising Leaflet so the map is created on
  // a sized container (otherwise fitBounds computes a world-level zoom on a 0px box).
  if (els.mapPanel) els.mapPanel.classList.add("leaflet-on");
  if (!ensureLeafletMap() || !state.features) return;
  leafletMap.invalidateSize();
  if (!leafletContextDone) {
    addContextMarkers(state.features.major_roads, "road", 12);
    addContextMarkers(state.features.crossings, "crossing", 11);
    addContextMarkers(state.features.generators, "generator", 11);
    leafletContextDone = true;
  }
  const topIds = new Set(state.candidates.slice(0, 30).map((row) => row.generator_id));
  const selectedId = state.selected && state.selected.generator_id;
  leafletCandidateLayer.clearLayers();
  const fitPoints = [];
  for (const p of state.features.candidates) {
    if (!topIds.has(p.generator_id) || !Number.isFinite(p.lon) || !Number.isFinite(p.lat)) continue;
    const score = p.route_review_priority_score || p.risk_score || 0;
    const size = Math.max(16, Math.min(28, score / 3.5));
    const marker = window.L.marker([p.lat, p.lon], {
      icon: categoryIcon("candidate", size, p.generator_id === selectedId ? "#0f172a" : "#ffffff"),
      title: `${String(p.name || p.generator_id)} — review priority ${String(score)}`,
      riseOnHover: true,
    }).addTo(leafletCandidateLayer);
    marker.on("click", () => selectCandidate(p.generator_id));
    fitPoints.push([p.lat, p.lon]);
  }
  if (!leafletFitted && fitPoints.length) {
    // Coarse data-driven view first so tiles load at the right place even before
    // the (just-revealed) canvas has been laid out...
    const avgLat = fitPoints.reduce((sum, pt) => sum + pt[0], 0) / fitPoints.length;
    const avgLon = fitPoints.reduce((sum, pt) => sum + pt[1], 0) / fitPoints.length;
    leafletMap.setView([avgLat, avgLon], 14);
    // ...then a precise fit once the browser has measured the real container size.
    requestAnimationFrame(() => {
      if (!leafletMap || leafletFitted || leafletMap.getSize().y <= 50) return;
      leafletMap.fitBounds(window.L.latLngBounds(fitPoints).pad(0.15));
      leafletFitted = true;
    });
  }
}

function renderMap() {
  if (leafletAvailable()) {
    renderMapLeaflet();
  } else {
    renderMapSvg();
  }
}

function renderMapSvg() {
  if (!els.map || !state.features) return;
  const allPoints = [
    ...state.features.generators,
    ...state.features.crossings,
    ...state.features.major_roads,
    ...state.features.candidates,
  ];
  const b = bounds(allPoints);

  function circle(point, cls, r, extra = "", title = "") {
    const p = project(point, b, MAP_BASE_W, MAP_BASE_H);
    const inner = title ? `<title>${title}</title>` : "";
    return `<circle class="${cls}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r}" ${extra}>${inner}</circle>`;
  }

  function square(point, cls, s, extra = "", title = "") {
    const p = project(point, b, MAP_BASE_W, MAP_BASE_H);
    const inner = title ? `<title>${title}</title>` : "";
    return `<rect class="${cls}" x="${(p.x - s).toFixed(1)}" y="${(p.y - s).toFixed(1)}" width="${s * 2}" height="${s * 2}" ${extra}>${inner}</rect>`;
  }

  function triangle(point, cls, s, extra = "", title = "") {
    const p = project(point, b, MAP_BASE_W, MAP_BASE_H);
    const inner = title ? `<title>${title}</title>` : "";
    const pts = `${p.x.toFixed(1)},${(p.y - s).toFixed(1)} ${(p.x - s).toFixed(1)},${(p.y + s).toFixed(1)} ${(p.x + s).toFixed(1)},${(p.y + s).toFixed(1)}`;
    return `<polygon class="${cls}" points="${pts}" ${extra}>${inner}</polygon>`;
  }

  function diamond(point, cls, s, extra = "", title = "") {
    const p = project(point, b, MAP_BASE_W, MAP_BASE_H);
    const inner = title ? `<title>${title}</title>` : "";
    const pts = `${p.x.toFixed(1)},${(p.y - s).toFixed(1)} ${(p.x + s).toFixed(1)},${p.y.toFixed(1)} ${p.x.toFixed(1)},${(p.y + s).toFixed(1)} ${(p.x - s).toFixed(1)},${p.y.toFixed(1)}`;
    return `<polygon class="${cls}" points="${pts}" ${extra}>${inner}</polygon>`;
  }

  const topCandidateIds = new Set(state.candidates.slice(0, 30).map((row) => row.generator_id));
  const selectedId = state.selected && state.selected.generator_id;
  const majorRoads = state.features.major_roads.map((p) => triangle(p, "road", 3));
  const crossings = state.features.crossings.map((p) => square(p, "crossing", p.has_signal_nearby ? 3.2 : 2.6));
  const generators = state.features.generators.map((p) => diamond(p, "generator", 2.9));
  const candidates = state.features.candidates
    .filter((p) => topCandidateIds.has(p.generator_id))
    .map((p) =>
      circle(
        p,
        selectedId === p.generator_id ? "candidate selected-candidate" : "candidate",
        Math.max(4, Math.min(10, (p.route_review_priority_score || p.risk_score) / 11)),
        `data-id="${escapeHtml(p.generator_id)}"`,
        `${escapeHtml(String(p.name || p.generator_id))} — review priority ${escapeHtml(String(p.route_review_priority_score || p.risk_score || ""))}`,
      ),
    );

  els.map.innerHTML = `
    <style>
      .road { fill: #ea580c; opacity: .55; }
      .crossing { fill: #059669; opacity: .8; }
      .generator { fill: #2563eb; opacity: .5; }
      .candidate { fill: #e11d48; stroke: #fff; stroke-width: 1.4; cursor: pointer; opacity: .95; }
      .selected-candidate { stroke: #0f172a; stroke-width: 2.2; opacity: 1; }
    </style>
    <rect x="0.5" y="0.5" width="${MAP_BASE_W - 1}" height="${MAP_BASE_H - 1}" fill="none" stroke="#cbd5e1" rx="8"></rect>
    ${majorRoads.join("")}
    ${crossings.join("")}
    ${generators.join("")}
    ${candidates.join("")}
  `;
  if (!state.mapView) {
    state.mapView = { x: 0, y: 0, w: MAP_BASE_W, h: MAP_BASE_H };
  }
  applyMapView();
  [...els.map.querySelectorAll(".candidate")].forEach((node) => {
    node.addEventListener("click", () => selectCandidate(node.dataset.id));
  });
}

function selectCandidate(id) {
  const row = state.candidates.find((item) => item.generator_id === id)
    || state.features.candidates.find((item) => item.generator_id === id);
  if (!row) return;
  state.selected = row;
  const decision = state.decisions[id] || { status: "unreviewed", note: "", assignee: "", updated_at_utc: "" };
  const reviewOptions = REVIEW_STATUS_LABELS
    .map(([value, label]) => `<option value="${value}" ${decision.status === value ? "selected" : ""}>${label}</option>`)
    .join("");
  const reviewSummary = state.decisionSummary
    ? `${state.decisionSummary.reviewed} reviewed · ${state.decisionSummary.to_review} queued · ${state.decisionSummary.dismissed} dismissed · ${state.decisionSummary.total_recorded} recorded`
    : "no review decisions yet";
  const score = row.route_aware_available ? row.route_review_priority_score : row.risk_score;
  const scoreLabel = row.route_aware_available ? "Route priority score" : "Risk score";
  const riskFlags = flagPills(row.risk_flags);
  const networkFlags = flagPills(row.network_flags);
  const dataQualityFlags = flagPills(row.data_quality_flags);
  els.detail.innerHTML = `
    <div class="candidate-heading">
      <span class="eyebrow">${escapeHtml(row.generator_id)} - ${escapeHtml(typeLabel(row.generator_type))}</span>
      <h3>${escapeHtml(row.name || "Unnamed location")}</h3>
    </div>
    <div class="detail-kpis">
      <div class="detail-kpi">
        <span>Nearest crossing</span>
        <b>${fmt(row.nearest_crossing_m, " m") || "n/a"}</b>
      </div>
      <div class="detail-kpi">
        <span>${escapeHtml(scoreLabel)}</span>
        <b>${score ?? "n/a"}</b>
      </div>
      <div class="detail-kpi">
        <span>Major road</span>
        <b>${fmt(row.nearest_major_road_m, " m") || "n/a"}</b>
      </div>
      <div class="detail-kpi">
        <span>Signals within 50 m</span>
        <b>${row.signals_within_50m ?? "n/a"}</b>
      </div>
    </div>
    ${row.route_aware_available ? `
      <div class="route-note">
        <b>Route-aware crossing:</b> ${fmt(row.route_nearest_crossing_m, " m")} - ${fmt(row.route_vs_straight_ratio)}x straight proxy - reachable crossings ${row.reachable_crossings}
      </div>
    ` : ""}
    <div class="review-callout"><span></span>${escapeHtml(row.review_wording)}</div>
    <div class="flag-section"><b>Risk flags</b><div>${riskFlags || `<span class="muted-inline">No mapped risk flags in current filter.</span>`}</div></div>
    ${row.route_aware_available ? `<div class="flag-section"><b>Network flags</b><div>${networkFlags || `<span class="muted-inline">No network flags.</span>`}</div></div>` : ""}
    <div class="flag-section"><b>Data-quality flags</b><div>${dataQualityFlags || `<span class="muted-inline">No data-quality flags.</span>`}</div></div>
    <div class="review-form">
      <div class="review-form-head"><b>Field review</b><span class="muted-inline">${escapeHtml(reviewSummary)}</span></div>
      <label>Status
        <select id="reviewStatus">${reviewOptions}</select>
      </label>
      <label>Assignee
        <input id="reviewAssignee" type="text" value="${escapeHtml(decision.assignee)}" placeholder="who inspects on-site" />
      </label>
      <label>Notes
        <textarea id="reviewNote" rows="3" placeholder="On-site review notes">${escapeHtml(decision.note)}</textarea>
      </label>
      <button id="saveReviewDecision" type="button">Save review state</button>
      <div class="small-note">${decision.updated_at_utc ? `Last updated ${escapeHtml(decision.updated_at_utc)}` : "Not yet reviewed."}</div>
    </div>
  `;
  const saveButton = document.getElementById("saveReviewDecision");
  if (saveButton) {
    saveButton.addEventListener("click", () => saveReviewDecision(row.generator_id));
  }
  renderTable();
  renderMap();
}

function exportVisibleCsv() {
  const headers = [
    "generator_id",
    "generator_type",
    "name",
    "nearest_crossing_m",
    "route_nearest_crossing_m",
    "route_vs_straight_ratio",
    "route_review_priority_score",
    "nearest_major_road_m",
    "risk_score",
    "network_flags",
    "risk_flags",
    "data_quality_flags",
  ];
  const lines = [headers.join(",")];
  for (const row of state.candidates) {
    lines.push(headers.map((key) => JSON.stringify(row[key] ?? "")).join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "georeview_visible_candidates.csv";
  a.click();
  URL.revokeObjectURL(url);
}

async function safeStep(fn) {
  // Per-panel isolation: a failure in one loader must not abort the rest of the
  // boot, so the core map/review-queue still renders even if a secondary panel
  // (mostly the internal tooling layer) errors.
  try {
    await fn();
  } catch (error) {
    console.error("init step failed:", error);
  }
}

// P1b: product-mode named views (Setup / Review / Reports). The router sets one
// body class (show-<view>) that the CSS uses to reveal only the active view's
// sections. Active only in product mode; inert in full mode (the workbench).
const VIEW_NAMES = ["setup", "review", "reports"];
const VIEW_TABS = {
  setup: function () { return els.tabSetup; },
  review: function () { return els.tabReview; },
  reports: function () { return els.tabReports; },
};

function setView(name) {
  const view = VIEW_NAMES.includes(name) ? name : "review";
  for (const candidate of VIEW_NAMES) {
    document.body.classList.toggle("show-" + candidate, candidate === view);
  }
  for (const candidate of VIEW_NAMES) {
    const tab = VIEW_TABS[candidate]();
    if (!tab) continue;
    const active = candidate === view;
    tab.setAttribute("aria-selected", active ? "true" : "false");
    tab.tabIndex = active ? 0 : -1;
  }
  // Re-sync Leaflet when the Review view (re)appears so it lays out at full size.
  if (leafletMap) {
    leafletMap.invalidateSize();
  }
}

function readHashView() {
  const raw = (location.hash || "").replace(/^#/, "").trim().toLowerCase();
  if (VIEW_NAMES.includes(raw)) {
    return raw;
  }
  const workspaceActive = Boolean(state.activeWorkspaceId) || state.candidates.length > 0;
  return workspaceActive ? "review" : "setup";
}

function initViewRouter() {
  if (!document.body.classList.contains("product-mode")) {
    return;
  }
  for (const candidate of VIEW_NAMES) {
    const tab = VIEW_TABS[candidate]();
    if (!tab) continue;
    tab.addEventListener("click", function (event) {
      event.preventDefault();
      location.hash = "#" + candidate;
    });
    tab.addEventListener("keydown", function (event) {
      const idx = VIEW_NAMES.indexOf(candidate);
      let nextIdx = null;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        nextIdx = (idx + 1) % VIEW_NAMES.length;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        nextIdx = (idx - 1 + VIEW_NAMES.length) % VIEW_NAMES.length;
      } else if (event.key === "Home") {
        nextIdx = 0;
      } else if (event.key === "End") {
        nextIdx = VIEW_NAMES.length - 1;
      }
      if (nextIdx === null) {
        return;
      }
      event.preventDefault();
      location.hash = "#" + VIEW_NAMES[nextIdx];
      const nextTab = VIEW_TABS[VIEW_NAMES[nextIdx]]();
      if (nextTab) {
        nextTab.focus();
      }
    });
  }
  window.addEventListener("hashchange", function () { setView(readHashView()); });
  setView(readHashView());
}

async function init() {
  setupControlVisibility();
  setupMapInteractions();
  // Read the backend run mode ("product" vs "full") at boot. /api/health is the
  // one endpoint always served even in product mode, so this fetch is safe in
  // both modes. Any failure (offline, parse error) falls back to full mode so
  // the default workbench keeps behaving exactly as before.
  let productMode = false;
  try {
    const health = await getJson("/api/health");
    productMode = health.mode === "product";
  } catch (error) {
    productMode = false;
  }
  document.body.classList.toggle("product-mode", productMode);
  await safeStep(async () => {
    state.sources = await getJson("/api/catalog/sources");
    state.templates = await getJson("/api/templates");
    populateCatalogControls();
  });
  const steps = [
    loadWorkspaceRegistry,
    loadDashboardWorkspace,
    loadPilotAreas,
    loadSourceOnboarding,
    loadLocalIntake,
    loadSourceImportGuardrails,
    loadSourceHandoff,
    loadSourceHandoffExecution,
    loadExecutionEvidencePackage,
    loadExecutionResultDiff,
    loadExecutionDiffGallery,
    loadExecutionDiffDetail,
    loadReproducibilityAuditPacket,
    loadReviewerAuditIndex,
    loadPortfolioExportLauncher,
    loadPortableReleasePackage,
    loadDemoScriptPack,
    loadVisualQALedger,
    loadVisualBaselineComparison,
    loadDemoArtifactCompleteness,
    loadVisualEvidenceCapture,
    loadVisualEvidenceReviewDiff,
    loadVisualEvidenceReviewAnnotations,
    loadVisualEvidenceSignoffPacket,
    loadFinalReviewerLaunchChecklist,
    loadRecruiterDemoBrief,
    loadPublicPortfolioPackage,
    loadDemoReviewPlaybook,
    loadGithubPublicationBundle,
    loadRepositoryPublicationQa,
    loadRepositoryExportHandoff,
    loadRepositoryDryRunReview,
    loadRepositoryFinalPackageReview,
    loadPublicReadmeCleanupReview,
    loadPublicRepositoryPolishPackage,
    loadRepositoryExportChecklist,
    loadAnalysisProfiles,
    loadProfileWorkspaces,
    loadProductArchitecture,
    loadReleaseReadiness,
    loadPortfolioDemo,
    loadPortfolioEvidenceBundle,
    loadBundleReviewChecklist,
    loadPortfolioNarrative,
    loadPortfolioHandoff,
    loadPortfolioEvidenceGallery,
    loadMultiPilotComparison,
    loadComparisonMapExports,
    loadProfileDashboard,
    loadScoringRules,
    loadPostgisBackend,
    loadProfileMapper,
    loadContractExecution,
    loadOsmTagQuality,
    loadTemplateAuthoring,
    loadAuthoredProfileRunner,
    loadProfilePromotion,
    loadExecutionQueue,
    loadDatasetPackages,
    loadJobs,
    loadAnalysisRuns,
    loadPortfolioReports,
    loadSourceProfile,
  ];
  // P1a: in product mode run only the product-core loaders (their endpoints are
  // in backend PRODUCT_API_PREFIXES, served in both modes); skipping the ~50
  // tooling loaders avoids 404 console noise against the hidden #fullWorkbench.
  // Full mode runs every loader in the original order. Nothing is removed.
  const coreLoaders = new Set([
    loadWorkspaceRegistry,
    loadDashboardWorkspace,
    loadPilotAreas,
    loadAnalysisProfiles,
    loadProfileWorkspaces,
    loadProfileDashboard,
    loadScoringRules,
    loadOsmTagQuality,
    loadJobs,
    loadAnalysisRuns,
    loadSourceProfile,
  ]);
  for (const step of steps) {
    if (productMode && !coreLoaders.has(step)) {
      continue;
    }
    await safeStep(step);
  }
  await safeStep(loadDashboardWorkspace);
  if (document.body.classList.contains("product-mode")) {
    initViewRouter();
  }
}

for (const el of [els.generatorType, els.minScore, els.noCrossing, els.majorRoad]) {
  el.addEventListener("input", loadCandidates);
}
if (els.showAdvancedControls) {
  els.showAdvancedControls.addEventListener("change", setupControlVisibility);
}
els.dashboardWorkspaceSelect.addEventListener("change", async () => {
  state.activeWorkspaceId = els.dashboardWorkspaceSelect.value;
  await loadDashboardWorkspace();
});
els.sourceSelect.addEventListener("change", async () => {
  await loadSourceProfile();
  await loadAnalysisProfiles();
});
els.templateSelect.addEventListener("change", async () => {
  await loadTemplateCheck();
  await planAnalysisWorkflow(true);
  await loadAnalysisProfiles();
});
els.refreshSourceOnboarding.addEventListener("click", refreshSourceOnboarding);
els.previewLocalIntake.addEventListener("click", previewLocalIntake);
els.createLocalIntakePlan.addEventListener("click", createLocalIntakePlan);
els.refreshSourceImportGuardrails.addEventListener("click", loadSourceImportGuardrails);
els.previewSourceImportGuardrails.addEventListener("click", previewSourceImportGuardrails);
els.createSourceImportReview.addEventListener("click", createSourceImportReview);
els.approveSourceImportReview.addEventListener("click", approveSourceImportReview);
els.refreshSourceHandoff.addEventListener("click", loadSourceHandoff);
els.createSourceHandoff.addEventListener("click", createSourceHandoff);
els.refreshSourceHandoffExecution.addEventListener("click", loadSourceHandoffExecution);
els.executeSourceHandoff.addEventListener("click", executeSourceHandoff);
els.refreshExecutionEvidencePackage.addEventListener("click", loadExecutionEvidencePackage);
els.createExecutionEvidencePackage.addEventListener("click", createExecutionEvidencePackage);
els.refreshExecutionResultDiff.addEventListener("click", loadExecutionResultDiff);
els.createExecutionResultDiff.addEventListener("click", createExecutionResultDiff);
els.refreshExecutionDiffGallery.addEventListener("click", loadExecutionDiffGallery);
els.createExecutionDiffGallery.addEventListener("click", createExecutionDiffGallery);
els.refreshExecutionDiffDetail.addEventListener("click", loadExecutionDiffDetail);
els.createExecutionDiffDetail.addEventListener("click", createExecutionDiffDetail);
els.refreshReproducibilityAuditPacket.addEventListener("click", loadReproducibilityAuditPacket);
els.createReproducibilityAuditPacket.addEventListener("click", createReproducibilityAuditPacket);
els.refreshReviewerAuditIndex.addEventListener("click", loadReviewerAuditIndex);
els.createReviewerAuditIndex.addEventListener("click", createReviewerAuditIndex);
els.refreshPortfolioExportLauncher.addEventListener("click", loadPortfolioExportLauncher);
els.createPortfolioExportLauncher.addEventListener("click", createPortfolioExportLauncher);
els.refreshPortableReleasePackage.addEventListener("click", loadPortableReleasePackage);
els.createPortableReleasePackage.addEventListener("click", createPortableReleasePackage);
els.refreshDemoScriptPack.addEventListener("click", loadDemoScriptPack);
els.createDemoScriptPack.addEventListener("click", createDemoScriptPack);
els.refreshVisualQALedger.addEventListener("click", loadVisualQALedger);
els.createVisualQALedger.addEventListener("click", createVisualQALedger);
els.refreshVisualBaselineComparison.addEventListener("click", loadVisualBaselineComparison);
els.createVisualBaselineComparison.addEventListener("click", createVisualBaselineComparison);
els.refreshDemoArtifactCompleteness.addEventListener("click", loadDemoArtifactCompleteness);
els.createDemoArtifactCompleteness.addEventListener("click", createDemoArtifactCompleteness);
els.refreshVisualEvidenceCapture.addEventListener("click", loadVisualEvidenceCapture);
els.createVisualEvidenceCapture.addEventListener("click", createVisualEvidenceCapture);
els.refreshVisualEvidenceReviewDiff.addEventListener("click", loadVisualEvidenceReviewDiff);
els.createVisualEvidenceReviewDiff.addEventListener("click", createVisualEvidenceReviewDiff);
els.refreshVisualEvidenceReviewAnnotations.addEventListener("click", loadVisualEvidenceReviewAnnotations);
els.createVisualEvidenceReviewAnnotations.addEventListener("click", createVisualEvidenceReviewAnnotations);
els.refreshVisualEvidenceSignoffPacket.addEventListener("click", loadVisualEvidenceSignoffPacket);
els.createVisualEvidenceSignoffPacket.addEventListener("click", createVisualEvidenceSignoffPacket);
els.refreshFinalReviewerLaunchChecklist.addEventListener("click", loadFinalReviewerLaunchChecklist);
els.createFinalReviewerLaunchChecklist.addEventListener("click", createFinalReviewerLaunchChecklist);
els.refreshRecruiterDemoBrief.addEventListener("click", loadRecruiterDemoBrief);
els.createRecruiterDemoBrief.addEventListener("click", createRecruiterDemoBrief);
els.refreshPublicPortfolioPackage.addEventListener("click", loadPublicPortfolioPackage);
els.createPublicPortfolioPackage.addEventListener("click", createPublicPortfolioPackage);
els.refreshDemoReviewPlaybook.addEventListener("click", loadDemoReviewPlaybook);
els.createDemoReviewPlaybook.addEventListener("click", createDemoReviewPlaybook);
els.refreshGithubPublicationBundle.addEventListener("click", loadGithubPublicationBundle);
els.createGithubPublicationBundle.addEventListener("click", createGithubPublicationBundle);
els.refreshRepositoryPublicationQa.addEventListener("click", loadRepositoryPublicationQa);
els.createRepositoryPublicationQa.addEventListener("click", createRepositoryPublicationQa);
els.refreshRepositoryExportHandoff.addEventListener("click", loadRepositoryExportHandoff);
els.createRepositoryExportHandoff.addEventListener("click", createRepositoryExportHandoff);
els.refreshRepositoryDryRunReview.addEventListener("click", loadRepositoryDryRunReview);
els.createRepositoryDryRunReview.addEventListener("click", createRepositoryDryRunReview);
els.refreshRepositoryFinalPackageReview.addEventListener("click", loadRepositoryFinalPackageReview);
els.createRepositoryFinalPackageReview.addEventListener("click", createRepositoryFinalPackageReview);
els.refreshPublicReadmeCleanupReview.addEventListener("click", loadPublicReadmeCleanupReview);
els.createPublicReadmeCleanupReview.addEventListener("click", createPublicReadmeCleanupReview);
els.refreshPublicRepositoryPolishPackage.addEventListener("click", loadPublicRepositoryPolishPackage);
els.createPublicRepositoryPolishPackage.addEventListener("click", createPublicRepositoryPolishPackage);
els.refreshRepositoryExportChecklist.addEventListener("click", loadRepositoryExportChecklist);
els.createRepositoryExportChecklist.addEventListener("click", createRepositoryExportChecklist);
els.refreshAnalysisProfiles.addEventListener("click", loadAnalysisProfiles);
els.runTransitProfile.addEventListener("click", runTransitProfile);
els.runParkProfile.addEventListener("click", runParkProfile);
els.refreshProfileWorkspaces.addEventListener("click", loadProfileWorkspaces);
els.refreshProductArchitecture.addEventListener("click", loadProductArchitecture);
els.refreshReleaseReadiness.addEventListener("click", loadReleaseReadiness);
els.createReleaseReadinessSnapshot.addEventListener("click", createReleaseReadinessSnapshot);
els.refreshPortfolioDemo.addEventListener("click", loadPortfolioDemo);
els.createPortfolioDemoSnapshot.addEventListener("click", createPortfolioDemoSnapshot);
els.refreshPortfolioEvidenceBundle.addEventListener("click", loadPortfolioEvidenceBundle);
els.createPortfolioEvidenceBundle.addEventListener("click", createPortfolioEvidenceBundle);
els.refreshBundleReviewChecklist.addEventListener("click", loadBundleReviewChecklist);
els.createBundleReviewChecklist.addEventListener("click", createBundleReviewChecklist);
els.refreshPortfolioNarrative.addEventListener("click", loadPortfolioNarrative);
els.createPortfolioNarrative.addEventListener("click", createPortfolioNarrative);
els.refreshPortfolioHandoff.addEventListener("click", loadPortfolioHandoff);
els.createPortfolioHandoff.addEventListener("click", createPortfolioHandoff);
els.refreshPortfolioEvidenceGallery.addEventListener("click", loadPortfolioEvidenceGallery);
els.createPortfolioEvidenceGallery.addEventListener("click", createPortfolioEvidenceGallery);
els.refreshMultiPilotComparison.addEventListener("click", loadMultiPilotComparison);
els.createMultiPilotComparison.addEventListener("click", createMultiPilotComparison);
els.refreshComparisonMapExports.addEventListener("click", loadComparisonMapExports);
els.createComparisonMapExport.addEventListener("click", createComparisonMapExport);
els.refreshProfileDashboard.addEventListener("click", loadProfileDashboardResults);
els.profileDashboardSelect.addEventListener("change", loadProfileDashboardResults);
els.refreshScoringRules.addEventListener("click", loadScoringRules);
els.refreshPostgisBackend.addEventListener("click", loadPostgisBackend);
els.createPostgisPlan.addEventListener("click", createPostgisPlan);
els.refreshProfileMapper.addEventListener("click", loadProfileMapper);
els.createProfileMapperPlan.addEventListener("click", createProfileMapperPlan);
els.refreshContractExecution.addEventListener("click", loadContractExecution);
els.createContractDryRun.addEventListener("click", createContractDryRun);
els.refreshOsmTagQuality.addEventListener("click", loadOsmTagQuality);
els.runOsmTagQuality.addEventListener("click", runOsmTagQuality);
els.refreshTemplateAuthoring.addEventListener("click", loadTemplateAuthoring);
els.createTemplateDraft.addEventListener("click", createTemplateDraft);
els.refreshAuthoredProfileRunner.addEventListener("click", loadAuthoredProfileRunner);
els.runAuthoredProfile.addEventListener("click", runAuthoredProfile);
els.enqueueAuthoredDraft.addEventListener("click", enqueueAuthoredDraft);
els.refreshProfilePromotion.addEventListener("click", loadProfilePromotion);
els.createProfilePromotionProposal.addEventListener("click", createProfilePromotionProposal);
els.approveProfilePromotionProposal.addEventListener("click", () => recordProfilePromotionDecision("approve"));
els.rejectProfilePromotionProposal.addEventListener("click", () => recordProfilePromotionDecision("reject"));
els.createProfileContractDiff.addEventListener("click", createProfileContractDiff);
els.createProfileApplicationPlan.addEventListener("click", createProfileApplicationPlan);
els.createProfileConfigApplyProposal.addEventListener("click", createProfileConfigApplyProposal);
els.createProfileRegressionPreview.addEventListener("click", createProfileRegressionPreview);
els.refreshExecutionQueue.addEventListener("click", loadExecutionQueue);
els.enqueueExecutionQueueJob.addEventListener("click", enqueueExecutionQueueJob);
els.refreshDatasetPackages.addEventListener("click", loadDatasetPackages);
els.createDatasetPackage.addEventListener("click", createDatasetPackage);
els.pilotSearch.addEventListener("input", loadPilotAreas);
els.pilotAreaSelect.addEventListener("change", async () => {
  await loadPilotPreflight();
  await loadAnalysisProfiles();
});
els.pilotRouteAware.addEventListener("change", async () => {
  await loadPilotPreflight();
  await loadAnalysisProfiles();
});
els.planAnalysisWorkflow.addEventListener("click", () => planAnalysisWorkflow(false));
els.startAnalysisWorkflow.addEventListener("click", startAnalysisWorkflow);
els.refreshAnalysisRuns.addEventListener("click", loadAnalysisRuns);
els.generatePortfolioReport.addEventListener("click", generatePortfolioReport);
els.generateTransitPortfolioReport.addEventListener("click", generateTransitPortfolioReport);
els.generateParkPortfolioReport.addEventListener("click", generateParkPortfolioReport);
els.generateProfileComparisonReport.addEventListener("click", generateProfileComparisonReport);
els.generateProfileExportBundle.addEventListener("click", generateProfileExportBundle);
els.comparePortfolioRuns.addEventListener("click", comparePortfolioRuns);
els.refreshPortfolioReports.addEventListener("click", loadPortfolioReports);
els.buildPilotWorkspace.addEventListener("click", buildPilotWorkspace);
if (els.buildSelectedPilotShortcut) {
  els.buildSelectedPilotShortcut.addEventListener("click", buildPilotWorkspace);
}
els.refreshJobs.addEventListener("click", loadJobs);
els.buildWorkspace.addEventListener("click", buildWorkspace);
els.buildGenericWorkspace.addEventListener("click", buildGenericWorkspace);
els.buildRouteAwareWorkspace.addEventListener("click", buildRouteAwareWorkspace);
els.exportCsv.addEventListener("click", exportVisibleCsv);
window.addEventListener("resize", renderMap);

init();

