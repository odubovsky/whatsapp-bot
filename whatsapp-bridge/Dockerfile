# Multi-stage build for WhatsApp Bridge
# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev sqlite-dev

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o whatsapp-client .

# Runtime stage
FROM alpine:latest

# Install runtime dependencies (wget for health check)
RUN apk add --no-cache ca-certificates sqlite wget

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/whatsapp-client /app/whatsapp-client

# Create directories for store
RUN mkdir -p /app/store /shared/store

# Make binary executable
RUN chmod +x /app/whatsapp-client

# Expose HTTP API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/api/send || exit 1

# Run the bridge
CMD ["/app/whatsapp-client"]

