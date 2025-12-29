import { useState, useRef } from 'react';
import { Send, Maximize2, Minimize2, Paperclip, X } from 'lucide-react';
import './ChatInput.css';

const MAX_FILE_SIZE = 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set([
  'txt', 'md', 'markdown', 'csv', 'json',
  'js', 'jsx', 'ts', 'tsx',
  'py', 'rb', 'go', 'java', 'c', 'h', 'cpp', 'hpp',
  'cs', 'php', 'rs', 'swift', 'kt', 'scala',
  'sh', 'bash', 'zsh', 'yml', 'yaml', 'toml', 'ini',
  'xml', 'html', 'css', 'scss', 'less', 'sql',
  'dart', 'lua', 'pl', 'ps1', 'bat', 'cmd', 'm', 'mm',
  'r', 'tex'
]);

const ACCEPT_ATTRIBUTE = [
  'text/*',
  ...Array.from(ALLOWED_EXTENSIONS).map((ext) => `.${ext}`),
].join(',');

const readFileContent = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result ?? '');
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });

const validateFile = (file) => {
  if (file.size > MAX_FILE_SIZE) {
    return `"${file.name}" exceeds the 1MB limit.`;
  }

  const extension = file.name.split('.').pop()?.toLowerCase();
  const isTextType = file.type && file.type.startsWith('text/');
  const isAllowedExtension = extension && ALLOWED_EXTENSIONS.has(extension);

  if (!isTextType && !isAllowedExtension) {
    return `"${file.name}" is not a supported text file.`;
  }

  return null;
};

const createFileId = (file) => `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`;

export default function ChatInput({
  onSend,
  isLoading,
  placeholder,
  submitLabel = 'Send',
  variant = 'main',
  layout = 'inline',
  showCancel = false,
  onCancel,
  allowExpand = true,
  autoFocus = false,
}) {
  const [inputValue, setInputValue] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [stagedFiles, setStagedFiles] = useState([]);
  const dragCounter = useRef(0);
  const fileInputRef = useRef(null);

  const canSend = (inputValue.trim() || stagedFiles.length > 0) && !isLoading;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSend) return;

    const content = inputValue.trim();
    if (typeof onSend === 'function') {
      onSend(content, stagedFiles);
    }
    setInputValue('');
    setStagedFiles([]);
    setErrorMessage('');
    setIsExpanded(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const addFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;

    setErrorMessage('');
    const incomingFiles = Array.from(fileList);
    const existingKeys = new Set(
      stagedFiles.map((file) => `${file.name}-${file.size}`)
    );

    const validFiles = [];
    const errors = [];

    for (const file of incomingFiles) {
      const duplicateKey = `${file.name}-${file.size}`;
      if (existingKeys.has(duplicateKey)) {
        continue;
      }

      const validationError = validateFile(file);
      if (validationError) {
        errors.push(validationError);
        continue;
      }

      validFiles.push(file);
    }

    if (errors.length > 0) {
      setErrorMessage(errors[0]);
    }

    if (validFiles.length === 0) return;

    try {
      const readResults = await Promise.all(
        validFiles.map(async (file) => ({
          id: createFileId(file),
          name: file.name,
          size: file.size,
          content: await readFileContent(file),
        }))
      );
      setStagedFiles((prev) => [...prev, ...readResults]);
    } catch (error) {
      setErrorMessage('One of the files could not be read.');
    }
  };

  const handleFilePicker = (e) => {
    const files = e.target.files;
    void addFiles(files);
    e.target.value = '';
  };

  const handleRemoveFile = (fileId) => {
    setStagedFiles((prev) => prev.filter((file) => file.id !== fileId));
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    if (isLoading) return;
    dragCounter.current += 1;
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragging(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (isLoading) return;
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (isLoading) return;
    dragCounter.current = 0;
    setIsDragging(false);
    void addFiles(e.dataTransfer.files);
  };

  const inputClasses = [
    'chat-input-root',
    variant,
    layout,
    isExpanded ? 'expanded' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={inputClasses}>
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <div
          className={`chat-input-body ${isDragging ? 'dragging' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {stagedFiles.length > 0 && (
            <div className="file-chip-row">
              {stagedFiles.map((file) => (
                <div key={file.id} className="file-chip">
                  <span className="file-chip-name">{file.name}</span>
                  <button
                    type="button"
                    className="file-chip-remove"
                    onClick={() => handleRemoveFile(file.id)}
                    aria-label={`Remove ${file.name}`}
                    disabled={isLoading}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="textarea-shell">
            <textarea
              className="chat-input-textarea"
              placeholder={placeholder}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={isExpanded ? 10 : 3}
              autoFocus={autoFocus}
            />
            <div className="input-controls">
              {allowExpand && (
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  title={isExpanded ? 'Collapse' : 'Expand'}
                  disabled={isLoading}
                >
                  {isExpanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                </button>
              )}
              <button
                type="button"
                className="icon-button"
                onClick={() => fileInputRef.current?.click()}
                title="Attach files"
                disabled={isLoading}
              >
                <Paperclip size={18} />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="file-input-hidden"
                onChange={handleFilePicker}
                accept={ACCEPT_ATTRIBUTE}
              />
            </div>
            {isDragging && (
              <div className="drop-overlay">
                <span>Drop files here</span>
              </div>
            )}
          </div>

          {errorMessage && (
            <div className="file-error" role="alert">
              {errorMessage}
            </div>
          )}
        </div>

        <div className="chat-input-actions">
          {showCancel && (
            <button
              type="button"
              className="chat-input-cancel"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="chat-input-send"
            disabled={!canSend}
          >
            <Send size={18} />
            <span>{submitLabel}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
