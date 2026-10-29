#!/bin/sh
set -eu
if [ -e .env ]; then
  printf '%s\n' 'Zachowano istniejący .env. Sprawdź ustawienia przed uruchomieniem.'
  exit 0
fi
command -v openssl >/dev/null 2>&1 || { printf '%s\n' 'Wymagany openssl do wygenerowania sekretów.' >&2; exit 1; }
umask 077
{
  printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)"
  printf 'SECRET_KEY=%s\n' "$(openssl rand -hex 48)"
  printf 'PUBLIC_URL=%s\n' "${PUBLIC_URL:-http://localhost:8080}"
  printf 'APP_BIND=%s\n' "${APP_BIND:-0.0.0.0}"
  printf 'APP_PORT=%s\n' "${APP_PORT:-8080}"
  printf '%s\n' 'IMAGE_PREFIX=ghcr.io/mdriverpl/perlylubuskie' 'IMAGE_TAG=latest'
} > .env
printf '%s\n' 'Utworzono .env z losowymi sekretami. Plik zawiera hasła — zachowaj go na serwerze.'
