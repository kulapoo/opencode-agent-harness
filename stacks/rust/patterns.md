---
paths:
  - "**/*.rs"
---
# Rust Patterns

> This file extends [common/patterns.md](../common/patterns.md) with Rust-specific content.

## Repository Pattern with Traits

Encapsulate data access behind a trait:

```rust
pub trait OrderRepository: Send + Sync {
    fn find_by_id(&self, id: u64) -> Result<Option<Order>, StorageError>;
    fn find_all(&self) -> Result<Vec<Order>, StorageError>;
    fn save(&self, order: &Order) -> Result<Order, StorageError>;
    fn delete(&self, id: u64) -> Result<(), StorageError>;
}
```

Concrete implementations handle storage details (Postgres, SQLite, in-memory for tests).

## Service Layer

Business logic in service structs; inject dependencies via constructor:

```rust
pub struct OrderService {
    repo: Box<dyn OrderRepository>,
    payment: Box<dyn PaymentGateway>,
}

impl OrderService {
    pub fn new(repo: Box<dyn OrderRepository>, payment: Box<dyn PaymentGateway>) -> Self {
        Self { repo, payment }
    }

    pub fn place_order(&self, request: CreateOrderRequest) -> anyhow::Result<OrderSummary> {
        let order = Order::from(request);
        self.payment.charge(order.total())?;
        let saved = self.repo.save(&order)?;
        Ok(OrderSummary::from(saved))
    }
}
```

## Newtype Pattern for Type Safety

Prevent argument mix-ups with distinct wrapper types:

```rust
struct UserId(u64);
struct OrderId(u64);

fn get_order(user: UserId, order: OrderId) -> anyhow::Result<Order> {
    // Can't accidentally swap user and order IDs at call sites
    todo!()
}
```

## Enum State Machines

Model states as enums — make illegal states unrepresentable:

```rust
enum ConnectionState {
    Disconnected,
    Connecting { attempt: u32 },
    Connected { session_id: String },
    Failed { reason: String, retries: u32 },
}

fn handle(state: &ConnectionState) {
    match state {
        ConnectionState::Disconnected => connect(),
        ConnectionState::Connecting { attempt } if *attempt > 3 => abort(),
        ConnectionState::Connecting { .. } => wait(),
        ConnectionState::Connected { session_id } => use_session(session_id),
        ConnectionState::Failed { retries, .. } if *retries < 5 => retry(),
        ConnectionState::Failed { reason, .. } => log_failure(reason),
    }
}
```

Always match exhaustively — no wildcard `_` for business-critical enums.

## Builder Pattern

Use for structs with many optional parameters:

```rust
pub struct ServerConfig {
    host: String,
    port: u16,
    max_connections: usize,
}

impl ServerConfig {
    pub fn builder(host: impl Into<String>, port: u16) -> ServerConfigBuilder {
        ServerConfigBuilder {
            host: host.into(),
            port,
            max_connections: 100,
        }
    }
}

pub struct ServerConfigBuilder {
    host: String,
    port: u16,
    max_connections: usize,
}

impl ServerConfigBuilder {
    pub fn max_connections(mut self, n: usize) -> Self {
        self.max_connections = n;
        self
    }

    pub fn build(self) -> ServerConfig {
        ServerConfig {
            host: self.host,
            port: self.port,
            max_connections: self.max_connections,
        }
    }
}
```

## Sealed Traits for Extensibility Control

Use a private module to seal a trait, preventing external implementations:

```rust
mod private {
    pub trait Sealed {}
}

pub trait Format: private::Sealed {
    fn encode(&self, data: &[u8]) -> Vec<u8>;
}

pub struct Json;
impl private::Sealed for Json {}
impl Format for Json {
    fn encode(&self, data: &[u8]) -> Vec<u8> { todo!() }
}
```

## API Response Envelope

Consistent API responses using a generic enum:

```rust
#[derive(Debug, serde::Serialize)]
#[serde(tag = "status")]
pub enum ApiResponse<T: serde::Serialize> {
    #[serde(rename = "ok")]
    Ok { data: T },
    #[serde(rename = "error")]
    Error { message: String },
}
```

## Contract Definition

Define the interface as a `trait` before implementing it:

```rust
#[async_trait]
pub trait TaskApi: Send + Sync {
    async fn create_task(&self, input: CreateTaskInput) -> Result<Task, ApiError>;
    async fn list_tasks(&self, params: ListTasksParams) -> Result<Paged<Task>, ApiError>;
    async fn get_task(&self, id: TaskId) -> Result<Task, ApiError>;
    async fn update_task(&self, id: TaskId, input: UpdateTaskInput) -> Result<Task, ApiError>;
    async fn delete_task(&self, id: TaskId) -> Result<(), ApiError>;
}
```

## Error Representation

Use a single error enum (e.g. `thiserror`) at module boundaries and
`Result<T, E>` in signatures — never `unwrap` on external input. Map to the
universal REST envelope (`{ code, message, details? }`) in the HTTP layer:

```rust
#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("validation failed")]
    Validation { details: Vec<ErrorDetail> },
    #[error("task {0} not found")]
    NotFound(TaskId),
    #[error("conflict: {0}")]
    Conflict(String),
}
```

## Boundary Validation

Use `serde` for deserialization at the edge; add `validator` or a custom
`Deserialize` impl for rules. After parsing, internal code trusts the type:

```rust
#[derive(Debug, Deserialize, Validate)]
pub struct CreateTaskInput {
    #[validate(length(min = 1, max = 200))]
    pub title: String,
    pub description: Option<String>,
}

async fn create(Validated(input): Validated<CreateTaskInput>) -> impl IntoResponse {
    let task = state.svc.create(input).await?;
    (StatusCode::CREATED, Json(task)).into_response()
}
```

## Additive Evolution

- New fields must be `Option<T>` (or carry `#[serde(default)]`) so old payloads
  still deserialize.
- Adding a required field is a breaking deserialization change.
- For enums used in `match`: adding a variant breaks arms that aren't `_` —
  surface that as a deliberate migration, not a silent change.
- Never rename a serialized field without `#[serde(alias = "oldName")]`.

## Variant Types

Use enums with data — exhaustive `match` makes illegal states unrepresentable:

```rust
pub enum TaskStatus {
    Pending,
    InProgress { assignee: UserId, started_at: DateTime<Utc> },
    Completed { completed_at: DateTime<Utc>, completed_by: UserId },
    Cancelled { reason: String, cancelled_at: DateTime<Utc> },
}
```

## Input/Output Separation

Separate request structs (caller-provided) from response structs
(server-generated fields included):

```rust
#[derive(Debug, Deserialize)]
pub struct CreateTaskInput {
    pub title: String,
    pub description: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct Task {
    pub id: TaskId,
    pub title: String,
    pub description: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: UserId,
}
```

## Opaque IDs

Use newtypes so distinct IDs are not interchangeable:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(transparent)]
pub struct TaskId(pub String);

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(transparent)]
pub struct UserId(pub String);

async fn get_task(id: TaskId) -> Result<Task, ApiError> { /* ... */ unimplemented!() }
```

## References

See skill: `rust-patterns` for comprehensive patterns including ownership, traits, generics, concurrency, and async.
