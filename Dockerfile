FROM golang:1.27.1-alpine AS builder
WORKDIR /app
COPY Go-backend/go.mod Go-backend/go.sum ./
RUN go mod download
COPY Go-backend/ .
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/main .
COPY Go-backend/db/migrations ./db/migrations
EXPOSE 8080
ENTRYPOINT [ "./main" ]