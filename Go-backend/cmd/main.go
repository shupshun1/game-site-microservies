package main

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/postgres"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	_ "github.com/jackc/pgx/v5/stdlib"
)

func main() {
	dbuser := os.Getenv("DB_USER")
	dbpass := os.Getenv("DB_PASSWORD")
	dbname := os.Getenv("DB_NAME")
	dbhost := os.Getenv("DB_HOST")
	dbport := os.Getenv("DB_PORT")
	dsn := fmt.Sprintf("postgres://%s:%s@%s:%v/%s?sslmode=%s", dbuser, dbpass, dbhost, dbport, dbname, "disable")
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		slog.Error("Failed to open DB connection", "err", err)
		os.Exit(1)
	}
	defer db.Close()
	errD := db.Ping()
	if errD != nil {
		slog.Error("Could not connect to database")
		os.Exit(1)
	}
	migr, err := migrate.New("file://db/migrations", dsn)
	if err != nil {
		slog.Error("Failed to create migrate instance")
		os.Exit(1)
	}
	if err := migr.Up(); err != nil && err != migrate.ErrNoChange {
		slog.Error("Failed to apply migrations", "err", err)
		os.Exit(1)
	} else {
		slog.Info("Migrations applied successfully!")
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Everything is fine"))
	})
	server := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	// Starting server in Go func
	go func() {
		slog.Info("Starting server on :8080")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("Server failed")
			os.Exit(1)
		}
	}()

	// Waiting for Ctrl + C or docker stop
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	slog.Info("Shutting down server...")

	// 5 seconds for finishing already existed requests

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*5)
	defer cancel()

	// Graceful shutdown

	if err := server.Shutdown(ctx); err != nil {
		slog.Error("Server was forced to shutdown")
		os.Exit(1)
	}

	slog.Info("Server exited properly")
}
