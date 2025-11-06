# Copilot Studio Knowledge Source Descriptions

## 1. BO API Specifications (idx-bo-swagger-json)

**Name:** BO Portal API Specifications

**Description:**
This knowledge source contains OpenAPI/Swagger specifications for 16 Back Office Portal APIs. Use this when users ask about:
- API endpoints, paths, and HTTP methods (GET, POST, PUT, DELETE)
- Request/response schemas and data models
- API parameters, query strings, and request bodies
- Available operations and their purposes
- API authentication and authorization requirements
- Module capabilities and features overview

**Modules covered:** CORE (BO Portal), BANKEXTENSIONS, CAMPAIGN, CMS, CRYPTOPAYMENTS, GAMIFICATION, INHOUSEBANK, JACKPOT, MAN (Manual Approval Network), REFERRALS, REWARDGAME, SBR (Sportsbook Regulatory), SC (Settings Configuration), SPL (Sportsbook Player Limits), STB (Sportsbook), TOURNAMENTS

**Best for:** "What endpoints...?", "How do I call...?", "What parameters does...?", "Show me the API schema for...", "What operations are available in...?"

**When to use:**
✓ User needs API documentation or endpoint information
✓ Questions about request/response formats
✓ Looking for available operations in a module
✓ Understanding API contracts and schemas
✓ High-level feature discovery across modules

**When NOT to use:**
✗ Questions about implementation details or code
✗ Looking for TypeScript interfaces or classes
✗ Debugging or code-level troubleshooting
✗ Type definitions or function signatures

---

## 2. BO TypeScript Client Code (idx-bo-code)

**Name:** BO Portal TypeScript Client Implementation

**Description:**
This knowledge source contains TypeScript client library code generated from the BO Portal APIs, including services, models, interfaces, and type definitions for 16 modules with 2,400+ files. Use this when users ask about:
- TypeScript interfaces, types, and classes
- Service implementations and method signatures
- Model definitions and DTOs (Data Transfer Objects)
- Enum values and constants
- Angular service injection and usage
- Type-safe API client usage patterns
- Implementation details and code structure

**Content includes:** Service classes (e.g., BonusService, TournamentService), model interfaces (DTOs, enums, search criteria), API client modules, type definitions (.d.ts files), and Angular dependency injection configurations

**Best for:** "Show me the interface for...", "What properties does...have?", "How is...implemented?", "What's the TypeScript type for...?", "Show me the service methods for...", "What enums are available for...?"

**When to use:**
✓ User needs TypeScript code examples
✓ Looking for interface or type definitions
✓ Questions about service methods or implementations
✓ Understanding DTOs and model structures
✓ Code integration and usage patterns
✓ Finding enum values or constants
✓ Troubleshooting type errors

**When NOT to use:**
✗ High-level API documentation questions
✗ REST endpoint paths and HTTP methods
✗ API authentication or general architecture
✗ Non-code documentation needs

---

## Orchestration Guidelines

**Query Analysis:**
1. Contains "endpoint", "API", "call", "request", "response" → Use idx-bo-swagger-json
2. Contains "interface", "type", "class", "implementation", "method", "property" → Use idx-bo-code
3. "How does X work?" → Start with swagger (architecture), then code (implementation)
4. "Show me X" → Determine if they want API docs (swagger) or code (implementation)

**Multi-Source Strategy:**
- For comprehensive answers, query swagger first for context, then code for implementation
- If code search returns too specific, fall back to swagger for broader context
- Always cite which source (API spec vs code) the information came from

**Module Names:** BANKEXTENSIONS, CAMPAIGN, CMS, CRYPTOPAYMENTS, GAMIFICATION, INHOUSEBANK, JACKPOT, MAN, REFERRALS, REWARDGAME, SBR, SC, SPL, STB, TOURNAMENTS, CORE

CORE = iCore default Back Office Portal

**Client/Customer Code mapping:**
MAN = Mansion
SBR = Superbet Romania
SC = SkyCity
SPL = Superbet Poland
STB = Stanley Bet

