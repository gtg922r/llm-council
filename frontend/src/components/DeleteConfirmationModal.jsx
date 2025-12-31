import Modal from './Modal';
import { AlertTriangle } from 'lucide-react';
import './DeleteConfirmationModal.css';

export default function DeleteConfirmationModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = "Delete Conversation",
  message = "Are you sure you want to delete this conversation forever? This action cannot be undone."
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="delete-modal-content">
        <div className="delete-modal-header">
          <AlertTriangle className="delete-modal-icon" size={24} />
          <h2>{title}</h2>
        </div>
        <p className="delete-modal-message">{message}</p>
        <div className="delete-modal-actions">
          <button 
            type="button" 
            className="delete-modal-button cancel" 
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            type="button" 
            className="delete-modal-button confirm" 
            onClick={onConfirm}
          >
            Delete
          </button>
        </div>
      </div>
    </Modal>
  );
}
