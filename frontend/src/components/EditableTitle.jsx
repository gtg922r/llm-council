import { useState, useEffect, useRef } from 'react';
import './EditableTitle.css';

export default function EditableTitle({ title, onSave }) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(title);
  const inputRef = useRef(null);

  useEffect(() => {
    setValue(title);
  }, [title]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setValue(title);
    }
  };

  const handleSave = () => {
    if (value.trim() && value !== title) {
      onSave(value.trim());
    } else {
      setValue(title);
    }
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        className="editable-title-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleSave}
      />
    );
  }

  return (
    <h2 
      className="editable-title-display" 
      onClick={() => setIsEditing(true)}
      title="Click to edit"
    >
      {title || 'New Conversation'}
    </h2>
  );
}
