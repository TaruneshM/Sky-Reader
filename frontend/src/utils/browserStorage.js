export function readStorage(storage, key) {
  try {
    return storage()?.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(storage, key, value) {
  try {
    if (value === null) storage()?.removeItem(key);
    else storage()?.setItem(key, value);
  } catch {
    // Restricted browser storage should not prevent using the app.
  }
}

export const local = () => window.localStorage;
export const session = () => window.sessionStorage;
