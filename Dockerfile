FROM golang:1.27.1-alpine AS builder
WORKDIR /app
COPY Go-backend/cmd/app/go.mod Go-backend/cmd/app/go.sum ./
RUN go mod download
COPY Go-backend/cmd/app/. .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM alpine:latest
COPY --from=builder /app/main .
COPY Go-backend/db/migrations ./db/migrations
EXPOSE 8080
ENTRYPOINT [ "./main" ]