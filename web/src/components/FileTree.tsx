import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  createFileTreeFile,
  createFileTreeFolder,
  createFileTreeLink,
  deleteFileTreeNode,
  listFileTree,
  updateFileTreeContent,
  type FileTreeNodeResponse,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { FileTextIcon, FolderIcon, LinkIcon, PlusIcon, TrashIcon } from "./icons";

interface Crumb {
  id: string;
  name: string;
}

export default function FileTree({
  projectId,
  refreshKey,
  onChange,
}: {
  projectId: string;
  refreshKey?: number;
  onChange?: () => void;
}) {
  const { token } = useAuth();

  const [nodes, setNodes] = useState<FileTreeNodeResponse[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<Crumb[]>([]);
  const [openFile, setOpenFile] = useState<FileTreeNodeResponse | null>(null);
  const [isEditingFile, setIsEditingFile] = useState(false);
  const [fileDraft, setFileDraft] = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [showNewLink, setShowNewLink] = useState(false);
  const [showNewFile, setShowNewFile] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [linkName, setLinkName] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const currentFolderId = breadcrumb.length > 0 ? breadcrumb[breadcrumb.length - 1].id : null;

  useEffect(() => {
    if (isEditingFile) return;
    if (token && projectId) void loadNodes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId, refreshKey]);

  async function loadNodes() {
    if (!token) return;
    try {
      setNodes(await listFileTree(token, projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file tree");
    }
  }

  function openFolder(node: FileTreeNodeResponse) {
    setOpenFile(null);
    setBreadcrumb((prev) => [...prev, { id: node.id, name: node.name }]);
  }

  function jumpTo(index: number) {
    setOpenFile(null);
    setBreadcrumb((prev) => prev.slice(0, index + 1));
  }

  function jumpToRoot() {
    setOpenFile(null);
    setBreadcrumb([]);
  }

  function viewFile(node: FileTreeNodeResponse) {
    setOpenFile(node);
    setIsEditingFile(false);
    setFileDraft(node.content ?? "");
  }

  function closeFile() {
    setOpenFile(null);
    setIsEditingFile(false);
  }

  function startEditingFile() {
    setFileDraft(openFile?.content ?? "");
    setIsEditingFile(true);
  }

  async function handleSaveFile() {
    if (!token || !openFile) return;
    try {
      const updated = await updateFileTreeContent(token, projectId, openFile.id, fileDraft);
      setOpenFile(updated);
      setIsEditingFile(false);
      await loadNodes();
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save file");
    }
  }

  async function handleCreateFolder() {
    if (!token || !folderName.trim()) return;
    try {
      await createFileTreeFolder(token, projectId, folderName.trim(), currentFolderId);
      setFolderName("");
      setShowNewFolder(false);
      await loadNodes();
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create folder");
    }
  }

  async function handleCreateLink() {
    if (!token || !linkName.trim() || !linkUrl.trim()) return;
    try {
      await createFileTreeLink(token, projectId, linkName.trim(), linkUrl.trim(), currentFolderId);
      setLinkName("");
      setLinkUrl("");
      setShowNewLink(false);
      await loadNodes();
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add link");
    }
  }

  async function handleCreateFile() {
    if (!token || !fileName.trim()) return;
    try {
      const created = await createFileTreeFile(token, projectId, fileName.trim(), "", currentFolderId);
      setFileName("");
      setShowNewFile(false);
      await loadNodes();
      onChange?.();
      viewFile(created);
      setIsEditingFile(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create file");
    }
  }

  async function handleDelete(node: FileTreeNodeResponse) {
    if (!token) return;
    const message =
      node.node_type === "folder"
        ? `Delete folder "${node.name}" and everything inside it?`
        : `Delete "${node.name}"?`;
    if (!window.confirm(message)) return;
    try {
      await deleteFileTreeNode(token, projectId, node.id);
      if (openFile?.id === node.id) closeFile();
      await loadNodes();
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  const visible = nodes
    .filter((node) => node.parent_id === currentFolderId)
    .sort((a, b) =>
      a.node_type === b.node_type ? a.name.localeCompare(b.name) : a.node_type === "folder" ? -1 : 1,
    );

  return (
    <section className="rounded-md border border-ink-800 bg-ink-900">
      <div className="flex flex-wrap items-center gap-2 border-b border-ink-800 px-4 py-2.5">
        <nav className="flex min-w-0 flex-1 items-center gap-1 text-sm">
          <button
            onClick={jumpToRoot}
            className={`truncate rounded px-1.5 py-0.5 transition-colors hover:bg-ink-800 ${
              currentFolderId === null && !openFile ? "font-medium text-slate-100" : "text-slate-400"
            }`}
          >
            Files
          </button>
          {breadcrumb.map((crumb, index) => (
            <span key={crumb.id} className="flex items-center gap-1">
              <span className="text-slate-600">/</span>
              <button
                onClick={() => jumpTo(index)}
                className={`truncate rounded px-1.5 py-0.5 transition-colors hover:bg-ink-800 ${
                  index === breadcrumb.length - 1 && !openFile
                    ? "font-medium text-slate-100"
                    : "text-slate-400"
                }`}
              >
                {crumb.name}
              </button>
            </span>
          ))}
          {openFile && (
            <span className="flex items-center gap-1">
              <span className="text-slate-600">/</span>
              <span className="truncate rounded px-1.5 py-0.5 font-medium text-slate-100">
                {openFile.name}
              </span>
            </span>
          )}
        </nav>

        {!openFile && (
          <div className="flex flex-shrink-0 flex-wrap items-center gap-2">
            <button
              onClick={() => {
                setShowNewFolder((prev) => !prev);
                setShowNewLink(false);
                setShowNewFile(false);
              }}
              className="flex items-center gap-1 rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              New folder
            </button>
            <button
              onClick={() => {
                setShowNewFile((prev) => !prev);
                setShowNewFolder(false);
                setShowNewLink(false);
              }}
              className="flex items-center gap-1 rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add file
            </button>
            <button
              onClick={() => {
                setShowNewLink((prev) => !prev);
                setShowNewFolder(false);
                setShowNewFile(false);
              }}
              className="flex items-center gap-1 rounded-md bg-ember-500 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-ember-600"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add link
            </button>
          </div>
        )}

        {openFile && !isEditingFile && (
          <div className="flex flex-shrink-0 items-center gap-2">
            <button
              onClick={startEditingFile}
              className="rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              Edit
            </button>
            <button
              onClick={closeFile}
              className="rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              Close
            </button>
          </div>
        )}

        {openFile && isEditingFile && (
          <div className="flex flex-shrink-0 items-center gap-2">
            <button
              onClick={handleSaveFile}
              className="rounded-md bg-ember-500 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-ember-600"
            >
              Save
            </button>
            <button
              onClick={() => setIsEditingFile(false)}
              className="rounded-md border border-ink-700 bg-ink-850 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:border-ink-600"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {error && <p className="px-4 pt-3 text-sm text-red-400">{error}</p>}

      {openFile ? (
        <div className="px-5 py-4">
          {isEditingFile ? (
            <textarea
              autoFocus
              value={fileDraft}
              onChange={(e) => setFileDraft(e.target.value)}
              rows={16}
              className="w-full resize-y rounded-md border border-ink-700 bg-ink-850 p-3 font-mono text-sm text-slate-100 outline-none focus:border-ember-500"
            />
          ) : openFile.content ? (
            <div className="markdown-body">
              <ReactMarkdown>{openFile.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-slate-500">This file is empty.</p>
          )}
        </div>
      ) : (
        <>
          {showNewFolder && (
            <div className="flex items-center gap-2 border-b border-ink-800 bg-ink-850 px-4 py-2.5">
              <input
                autoFocus
                type="text"
                placeholder="Folder name"
                value={folderName}
                onChange={(e) => setFolderName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                className="min-w-0 flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateFolder}
                className="flex-shrink-0 rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          )}

          {showNewFile && (
            <div className="flex items-center gap-2 border-b border-ink-800 bg-ink-850 px-4 py-2.5">
              <input
                autoFocus
                type="text"
                placeholder="File name (e.g. notes.md)"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFile()}
                className="min-w-0 flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateFile}
                className="flex-shrink-0 rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Create
              </button>
            </div>
          )}

          {showNewLink && (
            <div className="flex flex-wrap items-center gap-2 border-b border-ink-800 bg-ink-850 px-4 py-2.5">
              <input
                autoFocus
                type="text"
                placeholder="Name (e.g. Kickoff deck)"
                value={linkName}
                onChange={(e) => setLinkName(e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <input
                type="url"
                placeholder="https://..."
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateLink()}
                className="min-w-0 flex-[2] rounded-md border border-ink-700 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-ember-500"
              />
              <button
                onClick={handleCreateLink}
                className="flex-shrink-0 rounded-md bg-ember-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-ember-600"
              >
                Add
              </button>
            </div>
          )}

          {visible.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-slate-500">This folder is empty.</p>
          ) : (
            <ul className="divide-y divide-ink-800">
              {visible.map((node) => (
                <li
                  key={node.id}
                  className="group flex items-center gap-2.5 px-4 py-2 text-sm hover:bg-ink-850"
                >
                  {node.node_type === "folder" ? (
                    <>
                      <FolderIcon className="h-4 w-4 flex-shrink-0 text-slate-500" />
                      <button
                        onClick={() => openFolder(node)}
                        className="min-w-0 flex-1 truncate text-left text-slate-200 hover:text-ember-400 hover:underline"
                      >
                        {node.name}
                      </button>
                    </>
                  ) : node.node_type === "link" ? (
                    <>
                      <LinkIcon className="h-4 w-4 flex-shrink-0 text-slate-500" />
                      <a
                        href={node.url ?? "#"}
                        target="_blank"
                        rel="noreferrer"
                        className="min-w-0 flex-1 truncate text-slate-200 hover:text-ember-400 hover:underline"
                      >
                        {node.name}
                      </a>
                    </>
                  ) : (
                    <>
                      <FileTextIcon className="h-4 w-4 flex-shrink-0 text-slate-500" />
                      <button
                        onClick={() => viewFile(node)}
                        className="min-w-0 flex-1 truncate text-left text-slate-200 hover:text-ember-400 hover:underline"
                      >
                        {node.name}
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(node)}
                    title="Delete"
                    className="flex-shrink-0 text-slate-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
