// dynamic lookup
const key = process.env[keyName];
const v = import.meta.env.VITE_API_URL;
const { API_KEY, SECRET_TOKEN: renamed, DEFAULT_VALUE = 'x' } = process.env;
const ignored = process.env.NOT_REAL; // envsanity-ignore
const dup = process.env.API_KEY;
