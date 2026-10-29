package handlers

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"game-site-backend/internal/models"
	"game-site-backend/internal/storage"

	"golang.org/x/crypto/bcrypt"
)

type Handler struct {
	Storage *storage.Storage
}

func New(s *storage.Storage) *Handler {
	return &Handler{Storage: s}
}

func (h *Handler) Register(w http.ResponseWriter, r *http.Request) {
	if r := r.Method; r != http.MethodPost {
		http.Error(w, "Method is not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request models.RegisterRequest

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		slog.Error("Could not decode register attempt", "err", err)
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
	}

	if len(request.Username) < 2 {
		http.Error(w, "username must be at least 2 characters", http.StatusBadRequest)
		return
	}

	if len(request.Password) < 6 {
		http.Error(w, "Password must be at least 6 characters", http.StatusBadRequest)
		return
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(request.Password), bcrypt.DefaultCost)
	if err != nil {
		slog.Error("Failed to hash password", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	user, err := h.Storage.CreateUser(r.Context(), request.Username, string(hashedPassword))
	if err != nil {
		slog.Error("Could not create user", "err", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	resp := models.RegisterResponse{
		Status:  "ok",
		UserId:  user.ID,
		Message: "User created successfully",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)

	if err = json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("Failed to encode response", "err", err)
		return
	}
}
