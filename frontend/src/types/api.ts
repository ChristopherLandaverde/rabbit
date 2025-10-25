export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export interface ChannelAttribution {
  credit: number;
  conversions: number;
  revenue: number;
  confidence: number;
}

export interface AttributionResults {
  channel_attribution: Record<string, ChannelAttribution>;
  summary: AttributionSummary;
  journey_analysis?: JourneyAnalysis;
}

export interface AttributionSummary {
  total_conversions: number;
  total_revenue: number;
  average_journey_length: number;
  unique_customers: number;
  attribution_window_days: number;
}

export interface JourneyAnalysis {
  journey_lengths: Record<string, number>;
  top_conversion_paths: ConversionPath[];
  time_to_conversion: TimeToConversion;
}

export interface ConversionPath {
  path: string[];
  conversions: number;
  revenue: number;
}

export interface TimeToConversion {
  average_days: number;
  median_days: number;
  percentile_95_days: number;
}

export interface DataQuality {
  completeness: number;
  consistency: number;
  freshness: number;
  overall_quality: number;
  total_records: number;
  valid_records: number;
  duplicate_records: number;
}

export interface AnalysisMetadata {
  linking_method: string;
  confidence_score: number;
  processing_time: number;
  data_quality: DataQuality;
  warnings: string[];
}

export interface BusinessInsight {
  type: 'optimization' | 'warning' | 'information';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
}

export interface AttributionResponse {
  results: AttributionResults;
  metadata: AnalysisMetadata;
  insights?: BusinessInsight[];
}

export interface ValidationError {
  field: string;
  error_code: string;
  message: string;
  suggestion: string;
}

export interface SchemaDetection {
  detected_columns: Record<string, string>;
  confidence: number;
  required_columns_present: boolean;
}

export interface ValidationResponse {
  valid: boolean;
  schema_detection: SchemaDetection;
  data_quality?: DataQuality;
  errors: ValidationError[];
  recommendations: string[];
  warnings: string[];
}

export type AttributionModel = 'first_touch' | 'last_touch' | 'linear' | 'time_decay' | 'position_based';
export type LinkingMethod = 'auto' | 'customer_id' | 'session_email' | 'email_only' | 'aggregate';

export interface AnalysisConfig {
  model?: AttributionModel;
  linking_method?: LinkingMethod;
  attribution_window?: number;
  confidence_threshold?: number;
}
