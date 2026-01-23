/**
 * Firebase configuration and initialization.
 * 
 * Firebase Web API keys are designed to be public (restricted by Security Rules
 * and domain restrictions), but we use env vars for cleanliness and easy rotation.
 */
import { initializeApp } from 'firebase/app';
import { 
  initializeAuth,
  browserLocalPersistence,
  browserSessionPersistence,
  indexedDBLocalPersistence,
  inMemoryPersistence,
  GoogleAuthProvider 
} from 'firebase/auth';
import { getFirestore, initializeFirestore } from 'firebase/firestore';

const firebaseConfig = {
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize services
// Initialize auth with explicit persistence fallback chain
// This prevents "No available storage method found" errors in restrictive environments
export const auth = initializeAuth(app, {
  persistence: [
    indexedDBLocalPersistence,
    browserLocalPersistence,
    browserSessionPersistence,
    inMemoryPersistence
  ]
});
// Use the 'symposia' database instead of default
export const db = initializeFirestore(app, {}, 'symposia');
export const googleProvider = new GoogleAuthProvider();

export default app;
