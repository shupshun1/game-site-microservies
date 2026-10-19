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

	errQ := tx.QueryRowContext(ctx, `INSERT INTO users (username, password_hash, photo_url) 
	VALUES ($1, $2, $3) 
	RETURNING id, username, photo_url, created_at`, username, passwordHash, photo_url).Scan(&user.ID, &user.Username, &user.PhotoUrl, &user.CreatedAt)
	if errQ != nil {
		slog.Error("Could not create a new user", "err", err)
		return nil, errQ
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
