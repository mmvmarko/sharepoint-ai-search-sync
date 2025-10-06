# SharePoint AI Search Sync - Architecture Diagram

## Complete System Flow

```mermaid
graph TB
    %% SharePoint Source
    subgraph "SharePoint Online"
        SPO[SharePoint Sites<br/>Documents & Libraries]
        SPO_FILES[Word, PDF, PPT Files]
        SPO --> SPO_FILES
    end

    %% Sync Pipeline
    subgraph "Sync Pipeline"
        DELTA[Delta Detection<br/>delta_state.json]
        GRAPH[Microsoft Graph API<br/>Device Code Flow]
        SYNC[sharepoint_sync.py<br/>Download & Process]
        
        SPO_FILES -.->|Change Detection| DELTA
        DELTA --> GRAPH
        GRAPH --> SYNC
    end

    %% Azure Storage
    subgraph "Azure Blob Storage"
        BLOB[Blob Container<br/>sharepoint-ingestion]
        META[Metadata & ACL<br/>JSON Sidecars]
        
        SYNC --> BLOB
        SYNC --> META
    end

    %% Azure AI Search
    subgraph "Azure AI Search Service"
        DS[Data Source<br/>Blob Connection]
        SS[Skillset<br/>OCR, Text Extraction]
        IDX[Search Index<br/>Fields + Vector Schema]
        INDEXER[Indexer<br/>Scheduled Processing]
        VECTOR[Integrated Vectorization<br/>Azure OpenAI Embeddings]
        
        BLOB --> DS
        DS --> INDEXER
        SS --> INDEXER
        INDEXER --> IDX
        VECTOR --> IDX
    end

    %% Authentication & Authorization
    subgraph "Microsoft Entra ID"
        AAD[Azure AD Tenant]
        INTERNAL[Internal Users]
        GUEST[Guest Users - B2B]
        GROUPS[Security Groups]
        
        AAD --> INTERNAL
        AAD --> GUEST
        AAD --> GROUPS
    end

    %% Web Application
    subgraph "Web Application"
        WEBAPP[Web App Frontend]
        AUTH[Authentication<br/>PKCE/Auth Code Flow]
        PROFILE[User Profile<br/>Groups Resolution]
        
        WEBAPP --> AUTH
        AUTH --> AAD
        AUTH --> PROFILE
    end

    %% Search & Query
    subgraph "Query Processing"
        QUERY[User Query]
        FILTER[Security Filter<br/>ACL + Groups]
        SEARCH[Hybrid Search<br/>Vector + Keyword]
        RESULTS[Search Results<br/>Top-K Documents]
        
        WEBAPP --> QUERY
        PROFILE --> FILTER
        QUERY --> SEARCH
        FILTER --> SEARCH
        IDX --> SEARCH
        SEARCH --> RESULTS
    end

    %% AI Agent
    subgraph "Microsoft 365 Agents SDK"
        AGENT[Copilot Studio Agent]
        RAG[Retrieval Augmented Generation]
        RESPONSE[Grounded Response]
        
        RESULTS --> AGENT
        AGENT --> RAG
        RAG --> RESPONSE
        RESPONSE --> WEBAPP
    end

    %% Data Flow Styling
    classDef sourceData fill:#e1f5fe
    classDef processing fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef security fill:#fff3e0
    classDef aiAgent fill:#fce4ec

    class SPO,SPO_FILES sourceData
    class DELTA,GRAPH,SYNC,SS,INDEXER,VECTOR processing
    class BLOB,META,DS,IDX storage
    class AAD,INTERNAL,GUEST,GROUPS,AUTH,PROFILE,FILTER security
    class AGENT,RAG,RESPONSE aiAgent
```

## Key Integration Points

### 1. **Change Detection Flow**
```mermaid
sequenceDiagram
    participant SP as SharePoint
    participant DS as Delta State
    participant GR as Graph API
    participant SY as Sync Process
    
    SP->>DS: File modified/added
    DS->>GR: Check delta tokens
    GR->>SY: Return changed items
    SY->>SP: Download file content
    SY->>DS: Update state tracking
```

### 2. **Indexing Pipeline**
```mermaid
sequenceDiagram
    participant BL as Blob Storage
    participant IX as Indexer
    participant SK as Skillset
    participant AI as Azure OpenAI
    participant ID as Search Index
    
    BL->>IX: New/updated blob detected
    IX->>SK: Extract text content
    SK->>AI: Generate embeddings
    AI->>IX: Return vector embeddings
    IX->>ID: Store document + vectors
```

### 3. **User Query Flow**
```mermaid
sequenceDiagram
    participant U as User
    participant WA as Web App
    participant AD as Azure AD
    participant GR as Graph API
    participant SE as Search Engine
    participant AG as AI Agent
    
    U->>WA: Enter query
    WA->>AD: Authenticate user
    AD->>WA: Return token + claims
    WA->>GR: Get user groups
    GR->>WA: Return group membership
    WA->>SE: Search with ACL filter
    SE->>WA: Return filtered results
    WA->>AG: Send query + context
    AG->>WA: Return grounded answer
    WA->>U: Display response
```

## Security & Permissions Model

```mermaid
graph LR
    subgraph "Document ACL Storage"
        DOC[Document]
        ACL[ACL Field<br/>["group1", "group2", "Everyone"]]
        DOC --> ACL
    end
    
    subgraph "User Context"
        USER[User Login]
        TOKEN[Access Token]
        GROUPS[User Groups<br/>["group1", "group3"]]
        USER --> TOKEN
        TOKEN --> GROUPS
    end
    
    subgraph "Query Filter"
        FILTER[search.in(acl, 'group1,group3')]
        MATCH[Document Accessible]
        NOMATCH[Document Filtered Out]
    end
    
    ACL --> FILTER
    GROUPS --> FILTER
    FILTER --> MATCH
    FILTER --> NOMATCH
```

## Component Responsibilities

| Component | Primary Function | Key Files |
|-----------|------------------|-----------|
| **Sync Pipeline** | Change detection & file staging | `sharepoint_sync.py`, `main.py` |
| **Search Setup** | Index/indexer provisioning | `azure_search_setup.py`, `azure_search_integrated_vectorization.py` |
| **Configuration** | Settings management | `config/settings.py` |
| **Diagnostics** | Debugging & validation | `debug_*.py`, `check_*.py`, `explore_*.py` |
| **State Management** | Delta tracking | `delta_state.json` |

## Why Internal + Guest Users Work Seamlessly

1. **Unified Identity**: Both use Entra ID tokens with object IDs
2. **Group Membership**: Guests can be assigned to same security groups
3. **ACL Resolution**: Same group-based filtering logic applies
4. **Token Validation**: Azure AD handles authentication uniformly
5. **Agents SDK**: Operates on authenticated context regardless of user type

## Scaling Considerations

- **Blob Storage**: Handles large document volumes
- **Search Service**: Scales indexing and query workloads independently  
- **Vectorization**: Integrated pipeline eliminates separate embedding service
- **Caching**: Delta state prevents redundant processing
- **Security**: Group-based filtering scales with organizational structure