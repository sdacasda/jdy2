/*
 * SPDX-License-Identifier: AGPL-3.0-only
 * Copyright (c) 2023, daeuniverse Organization <team@v2raya.org>
 */

package graphql

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"strings"
	"unicode"

	"github.com/daeuniverse/dae-wing/db"
)

type MutationResolver struct{}

func (r *MutationResolver) CreateUser(args *struct {
	Username string
	Password string
}) (token string, err error) {
	if len(args.Password) < 6 || strings.IndexFunc(args.Password, unicode.IsLetter) < 0 || strings.IndexFunc(args.Password, unicode.IsNumber) < 0 {
		return "", fmt.Errorf("too weak password; should contain numbers and letters, and no less than 6 in length")
	}
	tx := db.BeginTx(context.TODO())
	defer func() {
		if err == nil {
			tx.Commit()
		} else {
			tx.Rollback()
		}
	}()
	// Check if there is already a user.
	n, err := numberUsers(tx)
	if err != nil {
		return "", err
	}
	if n > 0 {
		return "", fmt.Errorf("a user already exists")
	}
	// Hash password.
	var sec [32]byte
	if _, err = io.ReadFull(rand.Reader, sec[:]); err != nil {
		return "", err
	}
	secret := hex.EncodeToString(sec[:])
	hashedPassword, err := hashPassword([]byte(secret), args.Password)
	if err != nil {
		return "", err
	}
	// Create user.
	if err = tx.Model(&db.User{}).Create(&db.User{
		Username:     args.Username,
		PasswordHash: hashedPassword,
		JwtSecret:    secret,
	}).Error; err != nil {
		return "", err
	}
	// Return token.
	return getToken(tx, args.Username, args.Password)
}
