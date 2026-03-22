const TOKEN_KEY = 'upi_access_token';
const USER_KEY = 'upi_user';

export const saveAuth = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const getUser = () => {
  const u = localStorage.getItem(USER_KEY);
  return u ? JSON.parse(u) : null;
};

export const isLoggedIn = () => !!getToken();

export const logout = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const authHeaders = () => ({
  Authorization: `Bearer ${getToken()}`
});
