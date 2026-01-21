/**
 * Firebase configuration and initialization.
 */
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore, initializeFirestore } from 'firebase/firestore';

const firebaseConfig = {
  projectId: "pyronic-apps",
  appId: "1:427543310857:web:702ae82ac6b7604e537ed8",
  storageBucket: "pyronic-apps.firebasestorage.app",
  apiKey: "AIzaSyCf53RsceJN1gwlfQ6pvzylAyKBySvPs7c",
  authDomain: "pyronic-apps.firebaseapp.com",
  messagingSenderId: "427543310857"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize services
export const auth = getAuth(app);
// Use the 'symposia' database instead of default
export const db = initializeFirestore(app, {}, 'symposia');
export const googleProvider = new GoogleAuthProvider();

export default app;
