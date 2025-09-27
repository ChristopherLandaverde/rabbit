# Multi-Touch Attribution API Specification

## OpenAPI 3.0.3 Specification

```yaml
openapi: 3.0.3
info:
  title: Multi-Touch Attribution API
  description: |
    A flexible API that delivers multi-touch attribution insights from any marketing data.
    
    Features:
    - Adaptive identity resolution (Customer ID, Session-based, Email matching, Statistical modeling)
    - Multiple attribution models (First-touch, Last-touch, Linear, Time-decay, Position-based)
    - Confidence scoring based on data quality
    - Universal data ingestion (CSV, JSON, Parquet)
    
    Processing Pipeline:
    1. Data validation and schema detection
    2. Optimal linking method selection
    3. Customer journey reconstruction
    4. Attribution model application
    5. Results with confidence scoring
  version: 1.0.0
  contact:
    name: Attribution API Support
    email: support@attribution-api.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.attribution.example.com/v1
    description: Production server
  - url: https://staging-api.attribution.example.com/v1
    description: Staging server

security:
  - ApiKeyAuth: []

paths:
  /health:
    get:
      tags:
        - System
      summary: Health check endpoint
      operationId: getHealth
      responses:
        '200':
          description: API is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /attribution/analyze:
    post:
      tags:
        - Attribution
      summary: Analyze attribution from uploaded data
      operationId: analyzeAttribution
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                  description: Marketing data file (CSV, JSON, Parquet)
                model:
                  $ref: '#/components/schemas/AttributionModel'
                attribution_window:
                  type: integer
                  default: 30
                  minimum: 1
                  maximum: 365
                  description: Attribution window in days
                linking_method:
                  $ref: '#/components/schemas/LinkingMethod'
                confidence_threshold:
                  type: number
                  format: float
                  default: 0.7
                  minimum: 0.0
                  maximum: 1.0
                  description: Minimum confidence threshold for results
      responses:
        '200':
          description: Attribution analysis completed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AttributionResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '422':
          $ref: '#/components/responses/ValidationError'
        '413':
          $ref: '#/components/responses/FileTooLarge'
        '500':
          $ref: '#/components/responses/InternalError'

  /attribution/validate:
    post:
      tags:
        - Attribution
      summary: Validate data schema before processing
      operationId: validateDataSchema
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                  description: Data file to validate
      responses:
        '200':
          description: Data validation completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '422':
          $ref: '#/components/responses/ValidationError'

  /attribution/methods:
    get:
      tags:
        - Attribution
      summary: Get available attribution methods
      operationId: getAttributionMethods
      responses:
        '200':
          description: Available attribution methods
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MethodsResponse'

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    AttributionModel:
      type: string
      enum:
        - first_touch
        - last_touch
        - linear
        - time_decay
        - position_based
      default: linear
      description: Attribution model to apply

    LinkingMethod:
      type: string
      enum:
        - auto
        - customer_id
        - session_email
        - email_only
        - aggregate
      default: auto
      description: Method for linking touchpoints into journeys

    HealthResponse:
      type: object
      properties:
        status:
          type: string
          example: "healthy"
        timestamp:
          type: string
          format: date-time
        version:
          type: string
          example: "1.0.0"

    AttributionResponse:
      type: object
      required:
        - results
        - metadata
      properties:
        results:
          $ref: '#/components/schemas/AttributionResults'
        metadata:
          $ref: '#/components/schemas/AnalysisMetadata'
        insights:
          type: array
          items:
            $ref: '#/components/schemas/BusinessInsight'

    AttributionResults:
      type: object
      required:
        - channel_attribution
        - summary
      properties:
        channel_attribution:
          type: object
          additionalProperties:
            $ref: '#/components/schemas/ChannelAttribution'
        summary:
          $ref: '#/components/schemas/AttributionSummary'
        journey_analysis:
          $ref: '#/components/schemas/JourneyAnalysis'

    ChannelAttribution:
      type: object
      required:
        - credit
        - conversions
        - revenue
      properties:
        credit:
          type: number
          format: float
          description: Attribution credit (0.0 to 1.0)
        conversions:
          type: integer
          description: Number of attributed conversions
        revenue:
          type: number
          format: float
          description: Attributed revenue
        confidence:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
          description: Confidence score for this channel's attribution

    AttributionSummary:
      type: object
      properties:
        total_conversions:
          type: integer
        total_revenue:
          type: number
          format: float
        average_journey_length:
          type: number
          format: float
        unique_customers:
          type: integer
        attribution_window_days:
          type: integer

    JourneyAnalysis:
      type: object
      properties:
        journey_lengths:
          type: object
          description: Distribution of journey lengths
        top_conversion_paths:
          type: array
          items:
            $ref: '#/components/schemas/ConversionPath'
        time_to_conversion:
          $ref: '#/components/schemas/TimeToConversion'

    ConversionPath:
      type: object
      properties:
        path:
          type: array
          items:
            type: string
          description: Sequence of channels in the path
        conversions:
          type: integer
          description: Number of conversions for this path
        revenue:
          type: number
          format: float

    TimeToConversion:
      type: object
      properties:
        average_days:
          type: number
          format: float
        median_days:
          type: number
          format: float
        percentile_95_days:
          type: number
          format: float

    AnalysisMetadata:
      type: object
      required:
        - linking_method
        - confidence_score
        - processing_time
      properties:
        linking_method:
          $ref: '#/components/schemas/LinkingMethod'
        confidence_score:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
        processing_time:
          type: number
          format: float
          description: Processing time in seconds
        data_quality:
          $ref: '#/components/schemas/DataQuality'
        warnings:
          type: array
          items:
            type: string

    DataQuality:
      type: object
      properties:
        completeness:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
        consistency:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
        freshness:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
        total_records:
          type: integer
        valid_records:
          type: integer
        duplicate_records:
          type: integer

    BusinessInsight:
      type: object
      properties:
        type:
          type: string
          enum:
            - optimization
            - warning
            - information
        title:
          type: string
        description:
          type: string
        impact:
          type: string
          enum:
            - high
            - medium
            - low

    ValidationResponse:
      type: object
      required:
        - valid
        - schema_detection
      properties:
        valid:
          type: boolean
        schema_detection:
          $ref: '#/components/schemas/SchemaDetection'
        errors:
          type: array
          items:
            $ref: '#/components/schemas/ValidationError'
        recommendations:
          type: array
          items:
            type: string

    SchemaDetection:
      type: object
      properties:
        detected_columns:
          type: object
          additionalProperties:
            type: string
        suggested_mapping:
          type: object
          additionalProperties:
            type: string
        confidence:
          type: number
          format: float
        required_columns_present:
          type: boolean

    ValidationError:
      type: object
      properties:
        field:
          type: string
        error_code:
          type: string
        message:
          type: string
        suggestion:
          type: string

    MethodsResponse:
      type: object
      properties:
        attribution_models:
          type: array
          items:
            $ref: '#/components/schemas/AttributionModelInfo'
        linking_methods:
          type: array
          items:
            $ref: '#/components/schemas/LinkingMethodInfo'

    AttributionModelInfo:
      type: object
      properties:
        model:
          $ref: '#/components/schemas/AttributionModel'
        name:
          type: string
        description:
          type: string
        use_cases:
          type: array
          items:
            type: string

    LinkingMethodInfo:
      type: object
      properties:
        method:
          $ref: '#/components/schemas/LinkingMethod'
        name:
          type: string
        description:
          type: string
        requirements:
          type: array
          items:
            type: string

    Error:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
        message:
          type: string
        details:
          type: object
        timestamp:
          type: string
          format: date-time

  responses:
    BadRequest:
      description: Bad request - invalid parameters or data
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    ValidationError:
      description: Validation error - data format issues
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    FileTooLarge:
      description: File size exceeds maximum limit
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    InternalError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

  examples:
    SampleAttributionResponse:
      value:
        results:
          channel_attribution:
            google_ads:
              credit: 0.35
              conversions: 145
              revenue: 72500.00
              confidence: 0.89
            facebook:
              credit: 0.28
              conversions: 116
              revenue: 58000.00
              confidence: 0.85
            email:
              credit: 0.22
              conversions: 91
              revenue: 45500.00
              confidence: 0.95
            organic_search:
              credit: 0.15
              conversions: 62
              revenue: 31000.00
              confidence: 0.78
          summary:
            total_conversions: 414
            total_revenue: 207000.00
            average_journey_length: 3.2
            unique_customers: 298
            attribution_window_days: 30
        metadata:
          linking_method: session_email
          confidence_score: 0.87
          processing_time: 2.34
          data_quality:
            completeness: 0.94
            consistency: 0.91
            freshness: 0.89
            total_records: 15420
            valid_records: 14495
            duplicate_records: 68