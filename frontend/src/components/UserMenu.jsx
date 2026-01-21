/**
 * User menu dropdown showing user info and sign out option.
 */
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, User } from 'lucide-react';
import './UserMenu.css';

export default function UserMenu() {
  const { user, signOut } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    setIsOpen(false);
    try {
      await signOut();
    } catch (err) {
      console.error('Sign out failed:', err);
    }
  };

  if (!user) return null;

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {user.photoURL ? (
          <img
            src={user.photoURL}
            alt={user.displayName || 'User'}
            className="user-avatar"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="user-avatar-placeholder">
            <User size={18} />
          </div>
        )}
      </button>

      {isOpen && (
        <div className="user-menu-dropdown">
          <div className="user-menu-header">
            {user.photoURL ? (
              <img
                src={user.photoURL}
                alt={user.displayName || 'User'}
                className="user-menu-avatar"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="user-menu-avatar-placeholder">
                <User size={24} />
              </div>
            )}
            <div className="user-menu-info">
              <span className="user-menu-name">
                {user.displayName || 'User'}
              </span>
              <span className="user-menu-email">{user.email}</span>
            </div>
          </div>

          <div className="user-menu-divider" />

          <button className="user-menu-item" onClick={handleSignOut}>
            <LogOut size={16} />
            <span>Sign out</span>
          </button>
        </div>
      )}
    </div>
  );
}
