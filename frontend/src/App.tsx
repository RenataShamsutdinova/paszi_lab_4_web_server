
import React, { useEffect, useState } from "react";
import "./App.css";

// типы данных, которые приложение получает от backend

interface CurrentUser {
  id: number;
  login: string;
}

interface Resource {
  id: number;
  name: string;
  content: string;
  owner_id: number;
  created_at: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface PermissionOut {
  resource_id: number;
  user_id: number;
  can_read: boolean;
  can_update: boolean;
  can_delete: boolean;
}

interface PermissionSettings {
  can_read: boolean;
  can_update: boolean;
  can_delete: boolean;
}

interface ApiError {
  detail?: string | Array<{
    msg?: string;
    loc?: Array<string | number>;
  }>;
}

// адрес backend API

const API_URL = import.meta.env.DEV
  ? "http://127.0.0.1:8000"
  : ""; //при запуске Docker запросы будут уходить туда откуда пришли, то есть сначала в Nginx

// универсальная функция для запросов к backend
// добавляет токен авторизации и обрабатывает ошибки

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token: string | null = null
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "Произошла ошибка при обращении к серверу";

    try {
      const errorData: ApiError = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail
          .map((item) => item.msg ?? "Некорректные данные")
          .join(", ");
      }
    } catch {
      message = `Ошибка сервера: ${response.status}`;
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function App() {
  // состояние авторизации

  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [accessToken, setAccessToken] = useState<string | null>(
    sessionStorage.getItem("access_token")
  );

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  // состояние списка документов

  const [resources, setResources] = useState<Resource[]>([]);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [resourcesStatus, setResourcesStatus] = useState("");

  // состояние создания документа

  const [newResourceName, setNewResourceName] = useState("");
  const [newResourceContent, setNewResourceContent] = useState("");
  const [isCreatingResource, setIsCreatingResource] = useState(false);

  // состояние открытого документа

  const [selectedResource, setSelectedResource] =
    useState<Resource | null>(null);

  const [resourcePermissions, setResourcePermissions] =
    useState<PermissionOut | null>(null);

  const [isLoadingResource, setIsLoadingResource] = useState(false);
  const [resourceStatus, setResourceStatus] = useState("");

  // состояние редактирования документа

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editContent, setEditContent] = useState("");
  const [isSavingResource, setIsSavingResource] = useState(false);

  // состояние удаления документа

  const [isDeletingResource, setIsDeletingResource] = useState(false);

  // состояние выдачи прав доступа

  const [permissionLogin, setPermissionLogin] = useState("");

  const [permissionSettings, setPermissionSettings] =
    useState<PermissionSettings>({
      can_read: true,
      can_update: false,
      can_delete: false,
    });

  const [permissionStatus, setPermissionStatus] = useState("");
  const [isSavingPermission, setIsSavingPermission] = useState(false);

  // восстановление авторизации после перезагрузки страницы

  useEffect(() => {
    if (!accessToken) {
      setCurrentUser(null);
      return;
    }

    let isActive = true;

    async function restoreSession() {
      try {
        const user = await apiRequest<CurrentUser>(
          "/api/me",
          {},
          accessToken
        );

        if (isActive) {
          setCurrentUser(user);
        }
      } catch {
        if (isActive) {
          sessionStorage.removeItem("access_token");
          setAccessToken(null);
          setCurrentUser(null);
        }
      }
    }

    restoreSession();

    return () => {
      isActive = false;
    };
  }, [accessToken]);

  // загрузка доступных пользователю документов

  async function loadResources() {
    if (!accessToken) {
      return;
    }

    setIsLoadingResources(true);
    setResourcesStatus("");

    try {
      const data = await apiRequest<Resource[]>(
        "/api/resources",
        {},
        accessToken
      );

      setResources(data);
    } catch (error) {
      setResourcesStatus(
        error instanceof Error
          ? error.message
          : "Не удалось загрузить документы"
      );
    } finally {
      setIsLoadingResources(false);
    }
  }

  // обновление списка после входа и изменения документов

  useEffect(() => {
    if (accessToken && currentUser) {
      loadResources();
    } else {
      setResources([]);
    }
    // loadResources вызывается при изменении авторизации
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, currentUser]);

  // регистрация или вход в систему

  async function handleAuthSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setAuthStatus("");
    setIsSubmitting(true);

    try {
      if (authMode === "register") {
        await apiRequest(
          "/api/register",
          {
            method: "POST",
            body: JSON.stringify({
              login,
              password,
            }),
          }
        );

        setAuthMode("login");
        setPassword("");
        setAuthStatus("Регистрация прошла успешно. Теперь войдите в систему");
      } else {
        const tokenData = await apiRequest<TokenResponse>(
          "/api/login",
          {
            method: "POST",
            body: JSON.stringify({
              login,
              password,
            }),
          }
        );

        sessionStorage.setItem("access_token", tokenData.access_token);
        setAccessToken(tokenData.access_token);

        const user = await apiRequest<CurrentUser>(
          "/api/me",
          {},
          tokenData.access_token
        );

        setCurrentUser(user);
        setPassword("");
        setAuthStatus("");
      }
    } catch (error) {
      setAuthStatus(
        error instanceof Error ? error.message : "Ошибка авторизации"
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  // выход из учётной записи

  function handleLogout() {
    sessionStorage.removeItem("access_token");

    setAccessToken(null);
    setCurrentUser(null);
    setResources([]);

    setSelectedResource(null);
    setResourcePermissions(null);

    setIsEditing(false);
    setAuthStatus("");
    setResourcesStatus("");
    setResourceStatus("");
    setPermissionStatus("");

    setLogin("");
    setPassword("");
  }

  // создание нового документа

  async function handleCreateResource(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!newResourceName.trim() || !newResourceContent.trim()) {
      setResourcesStatus("Заполните название и содержимое документа");
      return;
    }

    setIsCreatingResource(true);
    setResourcesStatus("");

    try {
      await apiRequest<Resource>(
        "/api/resources",
        {
          method: "POST",
          body: JSON.stringify({
            name: newResourceName.trim(),
            content: newResourceContent,
          }),
        },
        accessToken
      );

      setNewResourceName("");
      setNewResourceContent("");

      await loadResources();
      setResourcesStatus("Документ успешно создан");
    } catch (error) {
      setResourcesStatus(
        error instanceof Error
          ? error.message
          : "Не удалось создать документ"
      );
    } finally {
      setIsCreatingResource(false);
    }
  }

  // открытие документа и получение прав текущего пользователя

  async function handleOpenResource(resourceId: number) {
    setIsLoadingResource(true);
    setResourceStatus("");
    setResourcePermissions(null);
    setSelectedResource(null);
    setIsEditing(false);
    setPermissionStatus("");

    try {
      const [resource, permissions] = await Promise.all([
        apiRequest<Resource>(
          `/api/resources/${resourceId}`,
          {},
          accessToken
        ),
        apiRequest<PermissionOut>(
          `/api/resources/${resourceId}/my-permissions`,
          {},
          accessToken
        ),
      ]);

      setSelectedResource(resource);
      setResourcePermissions(permissions);

      setEditName(resource.name);
      setEditContent(resource.content);
    } catch (error) {
      setResourceStatus(
        error instanceof Error
          ? error.message
          : "Не удалось открыть документ"
      );
    } finally {
      setIsLoadingResource(false);
    }
  }

  // закрытие окна документа

  function handleCloseResource() {
    setSelectedResource(null);
    setResourcePermissions(null);

    setIsEditing(false);
    setResourceStatus("");
    setPermissionStatus("");
    setPermissionLogin("");

    setPermissionSettings({
      can_read: true,
      can_update: false,
      can_delete: false,
    });
  }

  // определение владельца документа

  const isResourceOwner =
    selectedResource !== null &&
    currentUser !== null &&
    selectedResource.owner_id === currentUser.id;

  // проверка фактических прав текущего пользователя

  const canUpdateResource =
    isResourceOwner || resourcePermissions?.can_update === true;

  const canDeleteResource =
    isResourceOwner || resourcePermissions?.can_delete === true;

  // переход к редактированию

  function handleStartEditing() {
    if (!selectedResource || !canUpdateResource) {
      return;
    }

    setEditName(selectedResource.name);
    setEditContent(selectedResource.content);
    setIsEditing(true);
    setResourceStatus("");
  }

  // отмена редактирования

  function handleCancelEditing() {
    if (selectedResource) {
      setEditName(selectedResource.name);
      setEditContent(selectedResource.content);
    }

    setIsEditing(false);
    setResourceStatus("");
  }

  // сохранение изменений документа

  async function handleSaveResource(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!selectedResource || !canUpdateResource) {
      return;
    }

    if (!editName.trim() || !editContent.trim()) {
      setResourceStatus("Название и содержимое не должны быть пустыми");
      return;
    }

    setIsSavingResource(true);
    setResourceStatus("");

    try {
      const updatedResource = await apiRequest<Resource>(
        `/api/resources/${selectedResource.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            name: editName.trim(),
            content: editContent,
          }),
        },
        accessToken
      );

      setSelectedResource(updatedResource);
      setEditName(updatedResource.name);
      setEditContent(updatedResource.content);
      setIsEditing(false);

      await loadResources();

      setResourceStatus("Изменения успешно сохранены");
    } catch (error) {
      setResourceStatus(
        error instanceof Error
          ? error.message
          : "Не удалось сохранить изменения"
      );
    } finally {
      setIsSavingResource(false);
    }
  }

  // удаление документа

  async function handleDeleteResource() {
    if (!selectedResource || !canDeleteResource) {
      return;
    }

    const confirmed = window.confirm(
      `Вы действительно хотите удалить документ «${selectedResource.name}»?`
    );

    if (!confirmed) {
      return;
    }

    setIsDeletingResource(true);
    setResourceStatus("");

    try {
      await apiRequest(
        `/api/resources/${selectedResource.id}`,
        {
          method: "DELETE",
        },
        accessToken
      );

      handleCloseResource();
      await loadResources();
      setResourcesStatus("Документ успешно удалён");
    } catch (error) {
      setResourceStatus(
        error instanceof Error
          ? error.message
          : "Не удалось удалить документ"
      );
    } finally {
      setIsDeletingResource(false);
    }
  }

  // изменение настроек выдаваемых прав
  // для редактирования и удаления обязательно требуется чтение

  function handlePermissionChange(
    permission: keyof PermissionSettings,
    checked: boolean
  ) {
    setPermissionSettings((previous) => {
      if (permission === "can_read" && !checked) {
        return {
          can_read: false,
          can_update: false,
          can_delete: false,
        };
      }

      if (permission === "can_update" || permission === "can_delete") {
        return {
          ...previous,
          can_read: true,
          [permission]: checked,
        };
      }

      return {
        ...previous,
        [permission]: checked,
      };
    });
  }

  // выдача прав другому пользователю

  async function handleGrantPermission(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!selectedResource || !isResourceOwner) {
      return;
    }

    if (!permissionLogin.trim()) {
      setPermissionStatus("Введите логин пользователя");
      return;
    }

    setIsSavingPermission(true);
    setPermissionStatus("");

    try {
      const savedPermission = await apiRequest<PermissionOut>(
        `/api/resources/${selectedResource.id}/permissions`,
        {
          method: "POST",
          body: JSON.stringify({
            user_login: permissionLogin.trim(),
            can_read: permissionSettings.can_read,
            can_update: permissionSettings.can_update,
            can_delete: permissionSettings.can_delete,
          }),
        },
        accessToken
      );

      const granted: string[] = [];

      if (savedPermission.can_read) {
        granted.push("чтение");
      }

      if (savedPermission.can_update) {
        granted.push("изменение");
      }

      if (savedPermission.can_delete) {
        granted.push("удаление");
      }

      setPermissionStatus(
        granted.length > 0
          ? `Права сохранены: ${granted.join(", ")}`
          : "Права доступа сохранены без разрешённых операций"
      );

      setPermissionLogin("");
      setPermissionSettings({
        can_read: true,
        can_update: false,
        can_delete: false,
      });
    } catch (error) {
      setPermissionStatus(
        error instanceof Error
          ? error.message
          : "Не удалось выдать права доступа"
      );
    } finally {
      setIsSavingPermission(false);
    }
  }

  // экран регистрации и входа

  if (!accessToken || !currentUser) {
    return (
      <main className="auth-page">
        <section className="auth-card">

          <div className="auth-brand"><h1>DocSpace</h1></div>



          <p className="eyebrow">DOCUMENT MANAGEMENT</p>


          <p className="auth-description">
            Ваши документы ㆍ Безопасное хранение документов и управление доступом к ним
          </p>

          <div className="auth-tabs">
            <button
              type="button"
              className={authMode === "login" ? "auth-tab active" : "auth-tab"}
              onClick={() => {
                setAuthMode("login");
                setAuthStatus("");
              }}
            >
              Вход
            </button>

            <button
              type="button"
              className={
                authMode === "register" ? "auth-tab active" : "auth-tab"
              }
              onClick={() => {
                setAuthMode("register");
                setAuthStatus("");
              }}
            >
              Регистрация
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            <label htmlFor="login">Логин</label>

            <input
              id="login"
              type="text"
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              placeholder="Введите логин"
              autoComplete="username"
              required
            />

            <label htmlFor="password">Пароль</label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Введите пароль"
              autoComplete={
                authMode === "login" ? "current-password" : "new-password"
              }
              required
            />

            <button
              className="primary-button auth-submit"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? "Подождите..."
                : authMode === "login"
                  ? "Войти"
                  : "Создать аккаунт"}
            </button>
          </form>

          {authStatus && (
            <div className="status-message">{authStatus}</div>
          )}

          <p className="auth-footer">
            Документы доступны только авторизованным пользователям
          </p>
        </section>
      </main>
    );
  }

  // основной экран личного кабинета

  return (
    <main className="app-page">
      <header className="topbar">
        <div className="topbar-brand">

          <div>
            <strong>DocSpace</strong>
            <span>Управление документами</span>
          </div>
        </div>

        <div className="user-panel">
          <div className="user-avatar">
            {currentUser.login.charAt(0).toUpperCase()}
          </div>

          <div className="user-details">
            <span>Вы вошли как</span>
            <strong>{currentUser.login}</strong>
          </div>

          <button
            className="logout-button"
            type="button"
            onClick={handleLogout}
          >
            Выйти
          </button>
        </div>
      </header>

      <section className="dashboard">
        <div className="welcome-section">
          <div>
            <p className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</p>
            <h1>Мои документы</h1>
            <p className="section-description">
              Создавайте документы и управляйте доступом к ним
            </p>
          </div>

          <div className="document-counter">
            <span>{resources.length}</span>
            <small>
              {resources.length === 1
                ? "документ"
                : resources.length >= 2 && resources.length <= 4
                  ? "документа"
                  : "документов"}
            </small>
          </div>
        </div>

        <div className="dashboard-grid">
          <section className="panel create-panel">
            <div className="panel-heading">
              <div className="panel-icon">+</div>

              <div>
                <h2>Новый документ</h2>
                <p>Добавьте документ в своё хранилище</p>
              </div>
            </div>

            <form className="create-form" onSubmit={handleCreateResource}>
              <label htmlFor="resource-name">Название документа</label>

              <input
                id="resource-name"
                type="text"
                value={newResourceName}
                onChange={(event) => setNewResourceName(event.target.value)}
                placeholder="Например, Личный документ"
                required
              />

              <label htmlFor="resource-content">Содержимое</label>

              <textarea
                id="resource-content"
                value={newResourceContent}
                onChange={(event) =>
                  setNewResourceContent(event.target.value)
                }
                placeholder="Введите текст документа..."
                rows={6}
                required
              />

              <button
                className="primary-button"
                type="submit"
                disabled={isCreatingResource}
              >
                {isCreatingResource ? "Создание..." : "Создать документ"}
              </button>
            </form>
          </section>

          <section className="panel resources-panel">
            <div className="panel-heading resources-heading">
              <div className="panel-icon document-icon">▤</div>

              <div>
                <h2>Список документов</h2>
                <p>Ваши документы и документы, доступные вам</p>
              </div>

              <button
                className="refresh-button"
                type="button"
                onClick={loadResources}
                disabled={isLoadingResources}
                title="Обновить список"
              >
                ↻
              </button>
            </div>

            {isLoadingResources ? (
              <div className="empty-state">
                <div className="loading-spinner" />
                <p>Загрузка документов...</p>
              </div>
            ) : resources.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">▤</div>
                <strong>Пока нет документов</strong>
                <p>Создайте первый документ с помощью формы слева</p>
              </div>
            ) : (
              <ul className="resource-list">
                {resources.map((resource) => (
                  <li className="resource-list-item" key={resource.id}>
                    <div className="resource-info">
                      <div className="resource-file-icon">DOC</div>

                      <div className="resource-text">
                        <strong>{resource.name}</strong>

                        <span>
                          {resource.owner_id === currentUser.id
                            ? "Ваш документ"
                            : "Доступ предоставлен"}
                        </span>
                      </div>
                    </div>

                    <button
                      className="open-resource-button"
                      type="button"
                      onClick={() => handleOpenResource(resource.id)}
                    >
                      Открыть
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {resourcesStatus && (
          <div className="status-message dashboard-status">
            {resourcesStatus}
          </div>
        )}
      </section>

      {/* окно открытого документа */}

      {(selectedResource || isLoadingResource || resourceStatus) && (
        <div
          className="modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              handleCloseResource();
            }
          }}
        >
          <section
            className="resource-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="resource-modal-title"
          >
            <div className="modal-header">
              <div>
                <p className="eyebrow">ПРОСМОТР ДОКУМЕНТА</p>
                <h2 id="resource-modal-title">
                  {selectedResource?.name ?? "Документ"}
                </h2>
              </div>

              <button
                className="modal-close"
                type="button"
                onClick={handleCloseResource}
                aria-label="Закрыть"
              >
                ×
              </button>
            </div>

            {isLoadingResource ? (
              <div className="empty-state modal-loading">
                <div className="loading-spinner" />
                <p>Открываем документ...</p>
              </div>
            ) : selectedResource ? (
              <>
                <div className="modal-body">
                  {isEditing ? (
                    <form
                      className="edit-form"
                      onSubmit={handleSaveResource}
                    >
                      <label htmlFor="edit-name">Название документа</label>

                      <input
                        id="edit-name"
                        type="text"
                        value={editName}
                        onChange={(event) => setEditName(event.target.value)}
                        required
                      />

                      <label htmlFor="edit-content">
                        Содержимое документа
                      </label>

                      <textarea
                        id="edit-content"
                        value={editContent}
                        onChange={(event) =>
                          setEditContent(event.target.value)
                        }
                        rows={12}
                        required
                      />

                      <div className="form-actions">
                        <button
                          className="primary-button"
                          type="submit"
                          disabled={isSavingResource}
                        >
                          {isSavingResource
                            ? "Сохранение..."
                            : "Сохранить изменения"}
                        </button>

                        <button
                          className="secondary-button"
                          type="button"
                          onClick={handleCancelEditing}
                        >
                          Отмена
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="resource-details">
                      {selectedResource.content}
                    </div>
                  )}

                  {!isEditing && (
                    <div className="document-meta">
                      <span>
                        {isResourceOwner
                          ? "Владелец документа"
                          : "Документ предоставлен вам"}
                      </span>

                      {resourcePermissions && (
                        <span>
                          {[
                            resourcePermissions.can_read && "Чтение",
                            resourcePermissions.can_update && "Изменение",
                            resourcePermissions.can_delete && "Удаление",
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                      )}
                    </div>
                  )}

                  {resourceStatus && (
                    <div className="status-message">{resourceStatus}</div>
                  )}

                  {!isEditing && (
                    <div className="document-actions">
                      {canUpdateResource && (
                        <button
                          className="primary-button"
                          type="button"
                          onClick={handleStartEditing}
                        >
                          Редактировать
                        </button>
                      )}

                      {canDeleteResource && (
                        <button
                          className="danger-button"
                          type="button"
                          onClick={handleDeleteResource}
                          disabled={isDeletingResource}
                        >
                          {isDeletingResource ? "Удаление..." : "Удалить"}
                        </button>
                      )}
                    </div>
                  )}

                  {/* управление доступом доступно только владельцу */}

                  {isResourceOwner && !isEditing && (
                    <section className="permissions-section">
                      <div className="permissions-heading">
                        <div className="panel-icon access-icon">♧</div>

                        <div>
                          <h3>Управление доступом</h3>
                          <p>
                            Предоставьте другому пользователю права на документ
                          </p>
                        </div>
                      </div>

                      <form
                        className="permission-form"
                        onSubmit={handleGrantPermission}
                      >
                        <label htmlFor="permission-login">
                          Логин пользователя
                        </label>

                        <input
                          id="permission-login"
                          type="text"
                          value={permissionLogin}
                          onChange={(event) =>
                            setPermissionLogin(event.target.value)
                          }
                          placeholder="Введите логин пользователя"
                          required
                        />

                        <div className="permission-options">
                          <label className="permission-option">
                            <input
                              type="checkbox"
                              checked={permissionSettings.can_read}
                              onChange={(event) =>
                                handlePermissionChange(
                                  "can_read",
                                  event.target.checked
                                )
                              }
                            />

                            <span>
                              <strong>Чтение</strong>
                              <small>Просмотр содержимого документа</small>
                            </span>
                          </label>

                          <label className="permission-option">
                            <input
                              type="checkbox"
                              checked={permissionSettings.can_update}
                              onChange={(event) =>
                                handlePermissionChange(
                                  "can_update",
                                  event.target.checked
                                )
                              }
                            />

                            <span>
                              <strong>Изменение</strong>
                              <small>Редактирование документа</small>
                            </span>
                          </label>

                          <label className="permission-option">
                            <input
                              type="checkbox"
                              checked={permissionSettings.can_delete}
                              onChange={(event) =>
                                handlePermissionChange(
                                  "can_delete",
                                  event.target.checked
                                )
                              }
                            />

                            <span>
                              <strong>Удаление</strong>
                              <small>Удаление документа</small>
                            </span>
                          </label>
                        </div>

                        <button
                          className="primary-button"
                          type="submit"
                          disabled={isSavingPermission}
                        >
                          {isSavingPermission
                            ? "Сохранение..."
                            : "Сохранить права доступа"}
                        </button>
                      </form>

                      {permissionStatus && (
                        <div className="status-message">
                          {permissionStatus}
                        </div>
                      )}
                    </section>
                  )}
                </div>
              </>
            ) : (
              <div className="status-message">{resourceStatus}</div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

export default App;
