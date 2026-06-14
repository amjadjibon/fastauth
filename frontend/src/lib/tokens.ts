// In-memory token store — never persisted to localStorage or sessionStorage.
// Tokens are lost on page refresh (intentional: prevents XSS token theft).

let accessToken: string | null = null
let refreshToken: string | null = null

export function getTokens() {
  return { accessToken, refreshToken }
}

export function setTokens(at: string, rt: string) {
  accessToken = at
  refreshToken = rt
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
}
