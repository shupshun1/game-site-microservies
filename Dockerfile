FROM golang:1.27.1-alpine:3.24 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd

FROM alpine:latest
COPY --from=builder /app/main .
COPY --from=builder /app/db/migrations db/migartions
EXPOSE 8080
ENTRYPOINT [ "./main" ]