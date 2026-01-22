/**
 * Authentication context providing Firebase auth state to the app.
 * 
 * Supports two modes:
 * 1. Firebase auth (production) - Uses Firebase Google Sign-In
 * 2. Dev auth (development) - Uses a static token for easy testing
 * 
 * Dev auth is only available when the backend has DEV_AUTH=true.
 */
import { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react';
import { 
  onAuthStateChanged, 
  signInWithPopup, 
  signOut as firebaseSignOut 
} from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

export const AuthContext = createContext(null);

/**
 * Authentication states
 */
export const AuthState = {
  LOADING: 'loading',
  AUTHENTICATED: 'authenticated',
  UNAUTHENTICATED: 'unauthenticated',
  ERROR: 'error'
};

// Storage key for dev auth session
const DEV_AUTH_STORAGE_KEY = 'symposia_dev_auth';

/**
 * Provider component that wraps the app and provides auth state.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authState, setAuthState] = useState(AuthState.LOADING);
  const [error, setError] = useState(null);
  
  // Dev auth state
  const [devAuthAvailable, setDevAuthAvailable] = useState(false);
  const [devAuthInfo, setDevAuthInfo] = useState(null);
  const [isDevAuth, setIsDevAuth] = useState(false);

  // Check for dev auth availability on mount
  useEffect(() => {
    const checkDevAuth = async () => {
      try {
        const response = await fetch('/api/auth/dev-info');
        if (response.ok) {
          const data = await response.json();
          if (data.dev_auth_enabled) {
            setDevAuthAvailable(true);
            setDevAuthInfo(data);
            
            // Check if we have a stored dev auth session
            const storedDevAuth = sessionStorage.getItem(DEV_AUTH_STORAGE_KEY);
            if (storedDevAuth === 'true') {
              // Restore dev auth session
              setUser({
                uid: data.user.uid,
                email: data.user.email,
                displayName: data.user.displayName,
                photoURL: null
              });
              setIsDevAuth(true);
              setAuthState(AuthState.AUTHENTICATED);
              return; // Skip Firebase auth listener setup
            }
          }
        }
      } catch (err) {
        // Dev auth not available, continue with Firebase
        console.debug('Dev auth not available:', err.message);
      }
    };
    
    checkDevAuth();
  }, []);

  useEffect(() => {
    // Skip Firebase listener if using dev auth
    if (isDevAuth) return;
    
    const unsubscribe = onAuthStateChanged(
      auth,
      (firebaseUser) => {
        if (firebaseUser) {
          setUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email,
            displayName: firebaseUser.displayName,
            photoURL: firebaseUser.photoURL
          });
          setAuthState(AuthState.AUTHENTICATED);
          setError(null);
        } else {
          // Only set unauthenticated if not using dev auth
          if (!isDevAuth) {
            setUser(null);
            setAuthState(AuthState.UNAUTHENTICATED);
          }
        }
      },
      (err) => {
        console.error('Auth state change error:', err);
        setError(err.message);
        setAuthState(AuthState.ERROR);
      }
    );

    return () => unsubscribe();
  }, [isDevAuth]);

  /**
   * Sign in with Google popup.
   * @returns {Promise<void>}
   */
  const signInWithGoogle = async () => {
    try {
      setError(null);
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      // Handle specific error cases
      if (err.code === 'auth/popup-closed-by-user') {
        // User closed popup, not an error
        return;
      }
      console.error('Sign in error:', err);
      setError(err.message);
      throw err;
    }
  };

  /**
   * Sign in with dev auth (only available when DEV_AUTH=true on backend).
   * @returns {Promise<void>}
   */
  const signInWithDevAuth = useCallback(async () => {
    if (!devAuthAvailable || !devAuthInfo) {
      setError('Dev auth is not available');
      return;
    }
    
    try {
      setError(null);
      setUser({
        uid: devAuthInfo.user.uid,
        email: devAuthInfo.user.email,
        displayName: devAuthInfo.user.displayName,
        photoURL: null
      });
      setIsDevAuth(true);
      setAuthState(AuthState.AUTHENTICATED);
      sessionStorage.setItem(DEV_AUTH_STORAGE_KEY, 'true');
    } catch (err) {
      console.error('Dev sign in error:', err);
      setError(err.message);
      throw err;
    }
  }, [devAuthAvailable, devAuthInfo]);

  /**
   * Sign out the current user.
   * @returns {Promise<void>}
   */
  const signOut = async () => {
    try {
      if (isDevAuth) {
        // Clear dev auth session
        setUser(null);
        setIsDevAuth(false);
        setAuthState(AuthState.UNAUTHENTICATED);
        sessionStorage.removeItem(DEV_AUTH_STORAGE_KEY);
      } else {
        await firebaseSignOut(auth);
      }
    } catch (err) {
      console.error('Sign out error:', err);
      setError(err.message);
      throw err;
    }
  };

  /**
   * Get the current user's ID token for API calls.
   * @returns {Promise<string|null>}
   */
  const getIdToken = async () => {
    // Return dev token if using dev auth
    if (isDevAuth && devAuthInfo) {
      return devAuthInfo.token;
    }
    
    const currentUser = auth.currentUser;
    if (!currentUser) return null;
    try {
      return await currentUser.getIdToken();
    } catch (err) {
      console.error('Failed to get ID token:', err);
      return null;
    }
  };

  const value = useMemo(() => ({
    user,
    authState,
    error,
    signInWithGoogle,
    signInWithDevAuth,
    signOut,
    getIdToken,
    isAuthenticated: authState === AuthState.AUTHENTICATED,
    isLoading: authState === AuthState.LOADING,
    // Dev auth specific
    devAuthAvailable,
    isDevAuth
  }), [user, authState, error, signInWithDevAuth, devAuthAvailable, isDevAuth]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access auth context.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
