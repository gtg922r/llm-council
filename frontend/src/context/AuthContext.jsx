/**
 * Authentication context providing Firebase auth state to the app.
 */
import { createContext, useContext, useEffect, useState, useMemo } from 'react';
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

/**
 * Provider component that wraps the app and provides auth state.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authState, setAuthState] = useState(AuthState.LOADING);
  const [error, setError] = useState(null);

  useEffect(() => {
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
          setUser(null);
          setAuthState(AuthState.UNAUTHENTICATED);
        }
      },
      (err) => {
        console.error('Auth state change error:', err);
        setError(err.message);
        setAuthState(AuthState.ERROR);
      }
    );

    return () => unsubscribe();
  }, []);

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
   * Sign out the current user.
   * @returns {Promise<void>}
   */
  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
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
    signOut,
    getIdToken,
    isAuthenticated: authState === AuthState.AUTHENTICATED,
    isLoading: authState === AuthState.LOADING
  }), [user, authState, error]);

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
