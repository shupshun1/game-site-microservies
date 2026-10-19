package storage

import (
	"context"
	"game-site-backend/internal/models"
	"log/slog"
)

func (s *Storage) CreateUser(ctx context.Context, username, passwordHash, photo_url string) (*models.User, error) {
	// Start transaction
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		slog.Error("Could not create a transaction")
		return nil, err
	}
	defer tx.Rollback()

	var user models.User

	err = tx.QueryRowContext(ctx, `INSERT INTO users (username, password_hash) 
	VALUES ($1, $2) 
	RETURNING id, username, photo_url, created_at`, username, passwordHash).Scan(&user.ID, &user.Username, &user.PhotoUrl, &user.CreatedAt)
	if err != nil {
		slog.Error("Could not create a new user", "err", err)
		return nil, err
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO users_stats (user_id) VALUES ($1)`, user.ID)
	if err != nil {
		slog.Error("Could not insert a new user into user_stats", "err", err)
		return nil, err
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO users_skins (user_id) VALUES($1)`, user.ID)
	if err != nil {
		slog.Error("Could not insert a new user into users_skins", "err", err)
		return nil, err
	}

	if err = tx.Commit(); err != nil {
		slog.Error("Could not commit transaction", "err", err)
		return nil, err
	}

	return &user, nil
}

func (s *Storage) GetUserByUsername(ctx context.Context, username string) (*models.User, error) {
	var user models.User

	err := s.db.QueryRowContext(ctx, `SELECT id, username, password_hash, photo_url, created_at
	FROM users
	WHERE username = $1`, username).Scan(&user.ID, &user.Username, &user.PasswordHash, &user.PhotoUrl, &user.CreatedAt)
	if err != nil {
		slog.Error("Could not take user by username from users", "err", err)
		return nil, err
	}

	return &user, nil
}

func (s *Storage) GetUserByID(ctx context.Context, userId int) (*models.User, error) {
	var user models.User
	err := s.db.QueryRowContext(ctx, `SELECT id, username, photo_url, created_at FROM users WHERE id = $1`, userId).Scan(&user.ID, &user.Username, &user.PhotoUrl, &user.CreatedAt)
	if err != nil {
		slog.Error("Could not take user by ID from user", "err", err)
		return nil, err
	}

	return &user, nil
}
