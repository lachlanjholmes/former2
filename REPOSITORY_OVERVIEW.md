# Former2 Repository Overview

## What is Former2?

Former2 is a powerful Infrastructure-as-Code (IaC) generation tool that allows you to automatically generate CloudFormation templates, Terraform configurations, and other IaC formats from your existing AWS resources. It's designed to help with infrastructure documentation, migration, and reverse engineering of cloud deployments.

## Core Purpose

The primary goal of Former2 is to **reverse-engineer existing AWS infrastructure** by:

1. **Scanning your AWS account** using AWS APIs to discover existing resources
2. **Analyzing the configuration** of those resources
3. **Generating Infrastructure-as-Code templates** that can recreate those resources
4. **Supporting multiple output formats** including CloudFormation, Terraform, CDK, Pulumi, and more

## Key Features

### Multi-Format Output Support
- **CloudFormation YAML/JSON templates**
- **Terraform HCL configurations**
- **AWS CDK** (both v1 and v2) in multiple languages (TypeScript, Python, Java, C#)
- **CDK for Terraform** (CDKTF)
- **Pulumi** configurations
- **Troposphere** (Python CloudFormation library)
- **Visual diagrams** using embedded draw.io

### Comprehensive AWS Service Coverage
- **84% CloudFormation resource coverage** (945/1156 resources)
- **49% Terraform coverage**
- Supports **80+ AWS services** including:
  - Compute (EC2, Lambda, ECS, EKS, Batch)
  - Storage (S3, EFS, FSx)
  - Database (RDS, DynamoDB, ElastiCache, Neptune)
  - Networking (VPC, CloudFront, Route53, API Gateway)
  - Security (IAM, KMS, Secrets Manager)
  - Machine Learning (SageMaker, Rekognition)
  - Analytics (Athena, EMR, Kinesis)
  - And many more...

### Multiple Access Methods
- **Web Interface**: Browser-based UI at [former2.com](https://former2.com)
- **Command Line Interface**: npm package for automation
- **Self-Hosting**: Can be hosted locally for security requirements

## Architecture Overview

### Core Components

#### 1. Web Application (`index.html`, `js/app.js`)
- Single-page application built with jQuery and Bootstrap
- Provides intuitive interface for credential management, resource discovery, and template generation
- Uses AWS JavaScript SDK for direct API calls

#### 2. Browser Extension Helper
- **Purpose**: Bypasses CORS limitations for certain AWS services (S3, IAM)
- **Available for**: Chrome, Firefox, Microsoft Edge
- **Optional**: Not required for all services, but recommended for full functionality

#### 3. Service Modules (`js/services/`)
- **Individual service handlers**: Each AWS service has dedicated JavaScript files
- **Resource type definitions**: Defines how to discover, analyze, and convert resources
- **API call mapping**: Maps AWS API responses to IaC template properties

#### 4. CLI Tool (`cli/`)
- **Node.js-based command-line interface**
- **Automation-friendly**: Suitable for CI/CD pipelines
- **Filtering capabilities**: Advanced filtering and search functionality

#### 5. Template Generators
- **Multiple output engines**: Separate logic for each IaC format
- **Cross-referencing**: Handles resource dependencies and relationships
- **Parameter substitution**: Supports CloudFormation parameters and variables

### Data Flow

1. **Authentication**: User provides AWS credentials (Access Key, Secret Key, optional Session Token)
2. **Region Selection**: Choose AWS region to scan
3. **Service Discovery**: 
   - Manual service selection OR
   - Automated account scanning
4. **Resource Enumeration**: 
   - API calls to discover resources in selected services
   - Results displayed in categorized tables
5. **Resource Selection**: User selects which resources to include in templates
6. **Template Generation**: 
   - Analyzes selected resources
   - Resolves dependencies and relationships
   - Generates output in chosen format(s)
7. **Output**: Templates can be copied, downloaded, or imported directly to CloudFormation

## Key Files and Directories

### Root Directory
- **`index.html`**: Main web application entry point
- **`package.json`**: Project metadata and dependencies
- **`README.md`**: Primary project documentation
- **`RESOURCE_COVERAGE.md`**: Auto-generated coverage statistics
- **`HOSTING.md`**: Instructions for self-hosting
- **`Dockerfile`**: Container configuration for self-hosting

### JavaScript Core (`js/`)
- **`app.js`**: Main application logic and UI handling
- **`mappings.js`**: Resource type definitions and mappings
- **`datatables.js`**: Data table configuration and management
- **`services/*.js`**: Individual AWS service handlers (80+ files)

### CLI Tool (`cli/`)
- **`main.js`**: Command-line interface implementation
- **`README.md`**: CLI-specific documentation
- **`Dockerfile`**: CLI container configuration

### Assets
- **`css/`**: Stylesheets and UI themes
- **`img/`**: Images, icons, and AWS service logos
- **`fonts/`**: Web fonts and icon fonts
- **`lib/`**: Third-party JavaScript libraries

## Security Model

### Data Handling
- **Client-side processing**: All resource analysis happens in your browser/local machine
- **No data transmission**: Resource information never leaves your environment
- **Credential security**: AWS credentials stored only in memory, never persisted
- **HTTPS**: All external communication encrypted

### Permission Requirements
- **Read-only access recommended**: `ReadOnlyAccess` policy sufficient for discovery
- **Import feature**: Requires additional CloudFormation permissions if using import functionality
- **Least privilege**: Can work with minimal permissions for specific services

## Use Cases

### 1. Infrastructure Documentation
- **Document existing infrastructure** by generating readable IaC templates
- **Architecture visualization** through diagram generation
- **Compliance and auditing** with comprehensive resource coverage

### 2. Migration and Modernization
- **Cloud-to-cloud migration**: Export from one AWS account, import to another
- **Tool migration**: Move from manual management to Infrastructure-as-Code
- **Multi-cloud preparation**: Generate Terraform for potential multi-cloud deployment

### 3. Disaster Recovery
- **Infrastructure backup**: Generate templates as backup of current state
- **Region replication**: Recreate infrastructure in different regions
- **Quick restoration**: Restore services from generated templates

### 4. Development and Testing
- **Environment replication**: Create identical dev/test environments
- **Cost optimization**: Analyze and optimize resource configurations
- **Experimentation**: Safe testing with infrastructure as code

### 5. Learning and Training
- **Best practices**: Examine well-architected infrastructure patterns
- **IaC education**: Learn CloudFormation/Terraform from existing resources
- **AWS service exploration**: Understand service configurations and relationships

## Advanced Features

### Resource Relationships
- **Automatic dependency detection**: Identifies relationships between resources
- **Cross-service references**: Handles complex multi-service architectures
- **Related resources suggestions**: Recommends additional resources to include

### Filtering and Search
- **Text-based filtering**: Search resources by name, tags, or properties
- **Service-based filtering**: Include/exclude specific AWS services
- **Regex filtering**: Advanced pattern-based resource selection
- **Tag-based selection**: Filter resources by AWS tags

### Customization Options
- **Parameter substitution**: Replace hardcoded values with CloudFormation parameters
- **Logical ID strategies**: Different naming conventions for resource identifiers
- **Output formatting**: Configurable spacing, sorting, and organization
- **Default resource handling**: Include or exclude AWS default resources

## Limitations and Considerations

### Service Coverage
- Not all AWS services are supported (though coverage is extensive)
- Some resources may require manual adjustment post-generation
- Beta/preview AWS services may not be included

### Generated Template Quality
- Templates may need refinement for production use
- Some AWS-specific optimizations might be lost in translation
- Complex custom configurations may require manual review

### API Rate Limits
- Large accounts may hit AWS API rate limits during scanning
- Some services have API costs associated with discovery calls
- Scanning large infrastructures can be time-intensive

## Getting Started

### Web Interface (Recommended for beginners)
1. Visit [former2.com](https://former2.com) or self-host
2. Install browser extension for full service support
3. Enter AWS credentials
4. Select region and scan services
5. Choose resources and generate templates

### CLI Interface (Recommended for automation)
```bash
# Install globally
npm install -g former2

# Generate CloudFormation template
former2 generate --output-cloudformation infrastructure.yaml

# Generate Terraform with filtering
former2 generate --output-terraform main.tf --search-filter "production"
```

### Self-Hosting (Recommended for security-sensitive environments)
```bash
# Using Docker
docker build https://github.com/iann0036/former2.git -t former2
docker run -p 8080:80 former2

# Or clone and serve locally
git clone https://github.com/iann0036/former2.git
cd former2
python3 -m http.server 8080
```

## Contributing and Development

### Repository Structure
The project is well-organized with clear separation of concerns:
- **Frontend**: HTML/CSS/JavaScript single-page application
- **Backend logic**: Client-side JavaScript modules
- **CLI**: Separate Node.js application
- **Documentation**: Comprehensive markdown files

### Development Workflow
- **Service modules**: Each AWS service has its own JavaScript module
- **Resource coverage**: Coverage statistics auto-generated
- **Testing**: CLI tool includes debugging and validation features

### Extension Points
- **New services**: Add new AWS services by creating service modules
- **Output formats**: Add new IaC formats by extending generation logic
- **Filtering**: Enhance resource selection and filtering capabilities

## Conclusion

Former2 is a comprehensive solution for AWS infrastructure reverse-engineering and IaC generation. It bridges the gap between existing cloud infrastructure and modern Infrastructure-as-Code practices, making it an invaluable tool for cloud engineers, architects, and DevOps professionals.

Whether you're documenting existing infrastructure, planning migrations, preparing for disaster recovery, or simply learning about AWS best practices, Former2 provides the tools and flexibility to convert your running AWS resources into maintainable, version-controlled Infrastructure-as-Code templates.
