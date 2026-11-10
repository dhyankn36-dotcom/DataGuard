const state = {
  datasets: [],
  activeId: null,
  user: null,
  profile: null,
  columns: [],
  displayNames: new Map(),
  selectionRequest: 0,
  previewRequest: 0,
  previewOffset: 0,
  previewPageSize: 100,
};

const elements = {
  appShell: document.querySelector("#app-shell"),
  authScreen: document.querySelector("#auth-screen"),
  loginForm: document.querySelector("#login-form"),
  loginButton: document.querySelector("#login-button"),
  loginEmail: document.querySelector("#login-email"),
  loginPassword: document.querySelector("#login-password"),
  authError: document.querySelector("#auth-error"),
  resetHelpToggle: document.querySelector("#reset-help-toggle"),
  resetHelp: document.querySelector("#reset-help"),
  signedInUser: document.querySelector("#signed-in-user"),
  manageAccountsButton: document.querySelector("#manage-accounts-button"),
  accountDialog: document.querySelector("#account-dialog"),
  createAccountForm: document.querySelector("#create-account-form"),
  newAccountEmail: document.querySelector("#new-account-email"),
  newAccountPassword: document.querySelector("#new-account-password"),
  confirmAccountPassword: document.querySelector("#confirm-account-password"),
  accountFormMessage: document.querySelector("#account-form-message"),
  createAccountButton: document.querySelector("#create-account-button"),
  accountList: document.querySelector("#account-list"),
  refreshAccountsButton: document.querySelector("#refresh-accounts-button"),
  passwordDialog: document.querySelector("#password-dialog"),
  changePasswordForm: document.querySelector("#change-password-form"),
  currentPassword: document.querySelector("#current-password"),
  newPassword: document.querySelector("#new-password"),
  confirmNewPassword: document.querySelector("#confirm-new-password"),
  passwordFormMessage: document.querySelector("#password-form-message"),
  savePasswordButton: document.querySelector("#save-password-button"),
  renameDialog: document.querySelector("#rename-dialog"),
  renameForm: document.querySelector("#rename-form"),
  datasetFilename: document.querySelector("#dataset-filename"),
  renameMessage: document.querySelector("#rename-message"),
  saveRenameButton: document.querySelector("#save-rename-button"),
  fileInput: document.querySelector("#file-input"),
  dropZone: document.querySelector("#drop-zone"),
  uploadProgress: document.querySelector("#upload-progress"),
  uploadMessage: document.querySelector("#upload-message"),
  notice: document.querySelector("#notice"),
  datasetList: document.querySelector("#dataset-list"),
  datasetCount: document.querySelector("#dataset-count"),
  mobileDatasetPicker: document.querySelector("#mobile-dataset-picker"),
  mobileDatasetSelect: document.querySelector("#mobile-dataset-select"),
  apiStatus: document.querySelector("#api-status"),
  apiStatusLabel: document.querySelector("#api-status-label"),
  emptyState: document.querySelector("#empty-state"),
  dashboard: document.querySelector("#dashboard"),
  profileTab: document.querySelector("#profile-tab"),
  previewTab: document.querySelector("#preview-tab"),
  qualityView: document.querySelector("#quality-view"),
  previewView: document.querySelector("#preview-view"),
};

function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}

function formatStatistic(value) {
  return value == null
    ? "—"
    : new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showNotice(message, success = false) {
  elements.notice.textContent = message;
  elements.notice.classList.toggle("success", success);
  elements.notice.hidden = false;
}

function clearNotice() {
  elements.notice.hidden = true;
  elements.notice.textContent = "";
}

function setApiStatus(connected) {
  elements.apiStatus.classList.toggle("disconnected", !connected);
  elements.apiStatusLabel.textContent = connected ? "API connected" : "API unavailable";
}

function showAuthScreen(message = "") {
  state.selectionRequest += 1;
  state.previewRequest += 1;
  state.user = null;
  state.datasets = [];
  state.activeId = null;
  state.profile = null;
  state.columns = [];
  state.displayNames.clear();
  elements.datasetList.replaceChildren();
  elements.datasetCount.textContent = "0";
  elements.mobileDatasetSelect.replaceChildren();
  elements.mobileDatasetPicker.hidden = true;
  document.querySelector("#column-rows").replaceChildren();
  document.querySelector("#preview-head").replaceChildren();
  document.querySelector("#preview-rows").replaceChildren();
  elements.manageAccountsButton.hidden = true;
  elements.accountDialog.close();
  elements.passwordDialog.close();
  elements.renameDialog.close();
  elements.createAccountForm.reset();
  elements.changePasswordForm.reset();
  elements.renameForm.reset();
  elements.notice.hidden = true;
  elements.appShell.hidden = true;
  elements.authScreen.hidden = false;
  elements.authError.textContent = message;
  elements.authError.hidden = !message;
}

function showWorkspace(user) {
  state.user = user;
  elements.signedInUser.textContent = user.email;
  elements.manageAccountsButton.hidden = user.role !== "admin";
  elements.authScreen.hidden = true;
  elements.appShell.hidden = false;
}

async function requestJson(url, options) {
  const response = await fetch(url, { ...options, credentials: "include" });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.detail || `Request failed (${response.status}).`);
    error.status = response.status;
    if (response.status === 401 && url !== "/api/auth/login") {
      showAuthScreen("Your session expired. Please sign in again.");
    }
    throw error;
  }
  return result;
}

async function loadDatasets(selectId) {
  const result = await requestJson("/api/datasets");
  setApiStatus(true);
  state.datasets = result.datasets;
  renderDatasetList();
  if (!state.datasets.length) {
    state.activeId = null;
    state.profile = null;
    elements.dashboard.hidden = true;
    elements.emptyState.hidden = false;
    return;
  }

  const requested = selectId || state.activeId;
  const selected = state.datasets.find((dataset) => dataset.dataset_id === requested)
    || state.datasets[0];
  await selectDataset(selected.dataset_id);
}

function renderDatasetList() {
  elements.datasetCount.textContent = state.datasets.length;
  elements.datasetList.replaceChildren();
  elements.mobileDatasetPicker.hidden = state.datasets.length === 0;
  elements.mobileDatasetSelect.replaceChildren();

  if (!state.datasets.length) {
    const empty = document.createElement("p");
    empty.className = "sidebar-empty";
    empty.textContent = "Your datasets will appear here.";
    elements.datasetList.append(empty);
    return;
  }

  for (const dataset of state.datasets) {
    const option = document.createElement("option");
    option.value = dataset.dataset_id;
    option.textContent = state.displayNames.get(dataset.dataset_id) || dataset.filename;
    option.selected = dataset.dataset_id === state.activeId;
    elements.mobileDatasetSelect.append(option);
  }

  for (const dataset of state.datasets) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `dataset-item${dataset.dataset_id === state.activeId ? " selected" : ""}`;
    button.setAttribute("aria-current", dataset.dataset_id === state.activeId ? "true" : "false");

    const icon = document.createElement("span");
    icon.className = "dataset-file-icon";
    icon.textContent = dataset.file_type;
    const text = document.createElement("span");
    text.className = "dataset-item-text";
    const name = document.createElement("span");
    name.className = "dataset-item-name";
    name.textContent = state.displayNames.get(dataset.dataset_id) || dataset.filename;
    const meta = document.createElement("span");
    meta.className = "dataset-item-meta";
    meta.textContent = formatBytes(dataset.size_bytes);
    text.append(name, meta);
    button.append(icon, text);
    button.addEventListener("click", () => selectDataset(dataset.dataset_id));
    elements.datasetList.append(button);
  }
}

async function selectDataset(datasetId) {
  const requestId = ++state.selectionRequest;
  state.activeId = datasetId;
  state.previewOffset = 0;
  clearNotice();
  elements.emptyState.hidden = true;
  elements.dashboard.hidden = false;
  renderDatasetList();

  try {
    const result = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/profile`);
    if (requestId !== state.selectionRequest) return;
    state.profile = result.profile;
    state.columns = Object.entries(result.profile.columns).map(([name, details]) => ({
      name,
      ...details,
    }));
    renderProfile(state.displayNames.get(datasetId) || result.filename);
    await renderPreview(0, datasetId);
  } catch (error) {
    if (requestId !== state.selectionRequest) return;
    showNotice(error.message);
    elements.dashboard.hidden = true;
    elements.emptyState.hidden = state.datasets.length > 0;
  }
}

function renderProfile(filename) {
  const profile = state.profile;
  const dataset = state.datasets.find((item) => item.dataset_id === state.activeId);
  document.querySelector("#active-filename").textContent = filename;
  document.querySelector(".file-type-badge").textContent = dataset?.file_type || "DATA";
  document.querySelector("#export-report").href =
    `/api/datasets/${encodeURIComponent(state.activeId)}/report`;
  document.querySelector("#dataset-subtitle").textContent =
    `${formatBytes(dataset?.size_bytes || 0)} · ${formatNumber(profile.total_rows)} records`;
  document.querySelector("#total-rows").textContent = formatNumber(profile.total_rows);
  document.querySelector("#total-columns").textContent = formatNumber(profile.total_columns);
  document.querySelector("#missing-values").textContent =
    formatNumber(profile.total_missing_values);
  document.querySelector("#missing-caption").textContent =
    `${profile.total_rows ? ((profile.total_missing_values / (profile.total_rows * profile.total_columns)) * 100).toFixed(1) : "0.0"}% of all cells`;

  const cellCount = profile.total_rows * profile.total_columns;
  const missingRate = cellCount ? profile.total_missing_values / cellCount : 0;
  const duplicateRate = profile.total_rows ? profile.duplicate_rows / profile.total_rows : 0;
  const score = Math.max(0, Math.round(100 * (1 - missingRate) * (1 - duplicateRate)));
  document.querySelector("#quality-score").textContent = score;
  document.querySelector("#score-bar").style.width = `${score}%`;
  document.querySelector("#score-caption").textContent =
    `${formatNumber(profile.duplicate_rows)} duplicate rows · ${score >= 90 ? "Looking good" : "Room to improve"}`;

  renderColumns();
  renderInsights(profile);
}

function renderColumns() {
  const search = document.querySelector("#column-search").value.trim().toLowerCase();
  const body = document.querySelector("#column-rows");
  body.replaceChildren();
  const visible = state.columns.filter((column) => column.name.toLowerCase().includes(search));
  document.querySelector("#no-columns").hidden = visible.length > 0;

  for (const column of visible) {
    const completeness = Math.max(0, 100 - column.missing_percentage);
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    nameCell.className = "column-name";
    nameCell.textContent = column.name;
    nameCell.title = column.name;
    const typeCell = document.createElement("td");
    const type = document.createElement("span");
    type.className = "type-pill";
    type.textContent = column.data_type;
    typeCell.append(type);
    const completenessCell = document.createElement("td");
    const completenessWrap = document.createElement("div");
    completenessWrap.className = `completeness${completeness < 80 ? " low" : ""}`;
    const track = document.createElement("span");
    track.className = "completeness-track";
    const fill = document.createElement("span");
    fill.style.width = `${completeness}%`;
    track.append(fill);
    const percentage = document.createElement("span");
    percentage.className = "completeness-value";
    percentage.textContent = `${completeness.toFixed(1)}%`;
    const missing = document.createElement("span");
    missing.className = "missing-count";
    missing.textContent = `${formatNumber(column.missing_values)} missing`;
    completenessWrap.append(track, percentage, missing);
    completenessCell.append(completenessWrap);
    const uniqueCell = document.createElement("td");
    uniqueCell.textContent = formatNumber(column.unique_values);
    const duplicateCell = document.createElement("td");
    duplicateCell.textContent = formatNumber(column.duplicate_values);
    const statsCell = document.createElement("td");
    statsCell.className = "numeric-summary";
    if (column.statistics) {
      const { mean, median, minimum, maximum } = column.statistics;
      statsCell.textContent =
        `Mean ${formatStatistic(mean)} · Median ${formatStatistic(median)} · Range ${formatStatistic(minimum)}–${formatStatistic(maximum)}`;
      if (column.potential_outliers > 0) {
        const outliers = document.createElement("span");
        outliers.className = "outlier-count";
        outliers.textContent = `${formatNumber(column.potential_outliers)} outliers`;
        statsCell.append(outliers);
      }
    } else {
      statsCell.textContent = "—";
    }
    row.append(nameCell, typeCell, completenessCell, uniqueCell, duplicateCell, statsCell);
    body.append(row);
  }
}

function renderInsights(profile) {
  const container = document.querySelector("#insights-list");
  container.replaceChildren();
  const insights = [];
  if (profile.duplicate_rows) {
    insights.push({
      title: `${formatNumber(profile.duplicate_rows)} duplicate rows`,
      detail: "Repeated records can skew downstream analysis.",
      good: false,
    });
  }
  if (profile.total_missing_values) {
    insights.push({
      title: `${formatNumber(profile.total_missing_values)} missing values`,
      detail: "Review incomplete fields before using this data.",
      good: false,
    });
  }
  for (const column of state.columns) {
    if (column.is_empty) {
      insights.push({
        title: `${column.name} is entirely empty`,
        detail: "This column has no values and may be safe to remove.",
        good: false,
      });
    } else if (column.is_constant) {
      insights.push({
        title: `${column.name} has one distinct value`,
        detail: "A constant column may not add useful analysis.",
        good: false,
      });
    }
    if (column.non_finite_values > 0) {
      insights.push({
        title: `${formatNumber(column.non_finite_values)} non-finite values`,
        detail: `Review infinite values in ${column.name}.`,
        good: false,
      });
    }
    if (column.potential_outliers > 0) {
      insights.push({
        title: `${column.potential_outliers} potential outliers`,
        detail: `Check unusual values in ${column.name}.`,
        good: false,
      });
    }
  }
  if (!insights.length) {
    const good = document.createElement("div");
    good.className = "insight-empty";
    good.textContent = "No missing values, duplicate rows, or numeric outliers detected.";
    container.append(good);
    return;
  }

  for (const insight of insights.slice(0, 5)) {
    const item = document.createElement("div");
    item.className = "insight-item";
    const marker = document.createElement("span");
    marker.className = `insight-marker${insight.good ? " good" : ""}`;
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = insight.title;
    const detail = document.createElement("p");
    detail.textContent = insight.detail;
    content.append(title, detail);
    item.append(marker, content);
    container.append(item);
  }
}

async function deleteActiveDataset() {
  const dataset = state.datasets.find((item) => item.dataset_id === state.activeId);
  const filename = dataset
    ? state.displayNames.get(dataset.dataset_id) || dataset.filename
    : "";
  if (!dataset || !window.confirm(`Delete "${filename}"? This cannot be undone.`)) {
    return;
  }

  clearNotice();
  try {
    await requestJson(`/api/datasets/${encodeURIComponent(dataset.dataset_id)}`, {
      method: "DELETE",
    });
    state.activeId = null;
    state.displayNames.delete(dataset.dataset_id);
    await loadDatasets();
    showNotice(`${filename} was deleted.`, true);
  } catch (error) {
    showNotice(error.message);
  }
}

async function renderPreview(offset = state.previewOffset, datasetId = state.activeId) {
  const requestId = ++state.previewRequest;
  const result = await requestJson(
    `/api/datasets/${encodeURIComponent(datasetId)}/preview?limit=${state.previewPageSize}&offset=${offset}`,
  );
  if (requestId !== state.previewRequest || datasetId !== state.activeId) return;
  state.previewOffset = result.offset;
  const head = document.querySelector("#preview-head");
  const body = document.querySelector("#preview-rows");
  head.replaceChildren();
  body.replaceChildren();
  const headerRow = document.createElement("tr");
  for (const column of result.columns) {
    const cell = document.createElement("th");
    cell.textContent = column;
    headerRow.append(cell);
  }
  head.append(headerRow);
  for (const record of result.rows) {
    const row = document.createElement("tr");
    for (const column of result.columns) {
      const cell = document.createElement("td");
      const value = record[column];
      cell.textContent = value == null ? "—" : String(value);
      cell.title = cell.textContent;
      row.append(cell);
    }
    body.append(row);
  }
  document.querySelector("#preview-caption").textContent =
    `Rows ${formatNumber(result.rows.length ? result.offset + 1 : 0)}–${formatNumber(result.offset + result.rows.length)} of ${formatNumber(state.profile.total_rows)}.`;
  document.querySelector("#preview-page-label").textContent =
    `Page ${formatNumber(Math.floor(result.offset / result.limit) + 1)}`;
  document.querySelector("#preview-previous").disabled = result.offset === 0;
  document.querySelector("#preview-next").disabled =
    !result.has_more || result.offset + result.rows.length >= state.profile.total_rows;
}

async function changePreviewPage(offset) {
  try {
    await renderPreview(offset);
  } catch (error) {
    showNotice(error.message);
  } finally {
    const previous = document.querySelector("#preview-previous");
    const next = document.querySelector("#preview-next");
    previous.disabled = state.previewOffset === 0;
    next.disabled =
      !state.profile
      || state.previewOffset + state.previewPageSize >= state.profile.total_rows;
  }
}

async function downloadCleanedDataset() {
  const button = document.querySelector("#clean-export-button");
  const datasetId = state.activeId;
  if (!datasetId) return;

  button.disabled = true;
  clearNotice();
  try {
    const params = new URLSearchParams({
      missing_strategy: document.querySelector("#missing-strategy").value,
      remove_duplicates: String(document.querySelector("#remove-duplicates").checked),
    });
    const response = await fetch(
      `/api/datasets/${encodeURIComponent(datasetId)}/cleaned?${params}`,
      { credentials: "include" },
    );
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      if (response.status === 401) {
        showAuthScreen("Your session expired. Please sign in again.");
      }
      throw new Error(result.detail || `Export failed (${response.status}).`);
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `dataguard-cleaned-${datasetId}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    const removedRows = Number(response.headers.get("X-DataGuard-Removed-Incomplete-Rows") || 0);
    const removedDuplicates = Number(response.headers.get("X-DataGuard-Removed-Duplicate-Rows") || 0);
    const filledValues = Number(response.headers.get("X-DataGuard-Filled-Values") || 0);
    showNotice(
      `Clean CSV downloaded. Filled ${formatNumber(filledValues)} values, removed ${formatNumber(removedRows)} incomplete rows, and removed ${formatNumber(removedDuplicates)} duplicate rows.`,
      true,
    );
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
  }
}

async function uploadFile(file) {
  if (!file) return;
  clearNotice();
  const extension = file.name.split(".").pop().toLowerCase();
  if (!["csv", "xlsx"].includes(extension)) {
    showNotice("Choose a CSV or XLSX file.");
    return;
  }
  if (file.size > 20 * 1024 * 1024) {
    showNotice("The selected file is larger than 20 MB.");
    return;
  }
  elements.uploadProgress.hidden = false;
  elements.uploadMessage.textContent = `Uploading ${file.name}…`;
  try {
    const result = await requestJson("/api/datasets/upload", {
      method: "POST",
      body: (() => {
        const formData = new FormData();
        formData.append("file", file);
        return formData;
      })(),
    });
    state.displayNames.set(result.dataset_id, result.filename);
    elements.uploadMessage.textContent = "Building your quality report…";
    await loadDatasets(result.dataset_id);
    showNotice(`${file.name} is ready to explore.`, true);
    document.querySelector("#dashboard").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showNotice(error.message);
  } finally {
    elements.uploadProgress.hidden = true;
    elements.fileInput.value = "";
  }
}

function openFilePicker() {
  elements.fileInput.click();
}

async function signIn(event) {
  event.preventDefault();
  elements.authError.hidden = true;
  elements.loginButton.disabled = true;
  try {
    const result = await requestJson("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: elements.loginEmail.value,
        password: elements.loginPassword.value,
      }),
    });
    elements.loginPassword.value = "";
    showWorkspace(result.user);
    try {
      await loadDatasets();
    } catch (error) {
      setApiStatus(false);
      showNotice(error.message);
    }
  } catch (error) {
    elements.authError.textContent = error.message;
    elements.authError.hidden = false;
  } finally {
    elements.loginButton.disabled = false;
  }
}

async function signOut() {
  try {
    await requestJson("/api/auth/logout", { method: "POST" });
    state.datasets = [];
    showAuthScreen();
  } catch (error) {
    showNotice(error.message);
  }
}

function closeAccountDialog() {
  elements.accountDialog.close();
  elements.createAccountForm.reset();
  elements.accountFormMessage.hidden = true;
  elements.accountFormMessage.textContent = "";
  elements.accountFormMessage.classList.remove("success");
}

function closePasswordDialog() {
  elements.passwordDialog.close();
  elements.changePasswordForm.reset();
  elements.passwordFormMessage.hidden = true;
  elements.passwordFormMessage.textContent = "";
  elements.passwordFormMessage.classList.remove("success");
}

function closeRenameDialog() {
  elements.renameDialog.close();
  elements.renameForm.reset();
  elements.renameMessage.hidden = true;
  elements.renameMessage.textContent = "";
  elements.renameMessage.classList.remove("success");
}

async function renameDataset(event) {
  event.preventDefault();
  const datasetId = state.activeId;
  if (!datasetId) return;

  elements.saveRenameButton.disabled = true;
  elements.renameMessage.hidden = true;
  try {
    const result = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: elements.datasetFilename.value.trim() }),
    });
    state.displayNames.set(datasetId, result.filename);
    state.datasets = state.datasets.map((dataset) => dataset.dataset_id === datasetId
      ? { ...dataset, filename: result.filename }
      : dataset);
    renderDatasetList();
    document.querySelector("#active-filename").textContent = result.filename;
    closeRenameDialog();
    showNotice(`Dataset renamed to ${result.filename}.`, true);
  } catch (error) {
    elements.renameMessage.textContent = error.message;
    elements.renameMessage.classList.remove("success");
    elements.renameMessage.hidden = false;
  } finally {
    elements.saveRenameButton.disabled = false;
  }
}

async function changePassword(event) {
  event.preventDefault();
  const newPassword = elements.newPassword.value;
  if (newPassword !== elements.confirmNewPassword.value) {
    elements.passwordFormMessage.textContent = "The new passwords do not match.";
    elements.passwordFormMessage.classList.remove("success");
    elements.passwordFormMessage.hidden = false;
    elements.confirmNewPassword.focus();
    return;
  }

  elements.savePasswordButton.disabled = true;
  elements.passwordFormMessage.hidden = true;
  try {
    const result = await requestJson("/api/auth/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: elements.currentPassword.value,
        new_password: newPassword,
      }),
    });
    elements.passwordFormMessage.textContent = result.message;
    elements.passwordFormMessage.classList.add("success");
    elements.passwordFormMessage.hidden = false;
    elements.changePasswordForm.reset();
  } catch (error) {
    elements.passwordFormMessage.textContent = error.message;
    elements.passwordFormMessage.classList.remove("success");
    elements.passwordFormMessage.hidden = false;
  } finally {
    elements.savePasswordButton.disabled = false;
  }
}

async function createAccount(event) {
  event.preventDefault();
  const password = elements.newAccountPassword.value;
  if (password !== elements.confirmAccountPassword.value) {
    elements.accountFormMessage.textContent = "The passwords do not match.";
    elements.accountFormMessage.classList.remove("success");
    elements.accountFormMessage.hidden = false;
    elements.confirmAccountPassword.focus();
    return;
  }

  elements.createAccountButton.disabled = true;
  elements.accountFormMessage.hidden = true;
  try {
    const result = await requestJson("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: elements.newAccountEmail.value.trim(),
        password,
      }),
    });
    elements.accountFormMessage.textContent =
      `Account created for ${result.user.email}. Share the temporary password securely.`;
    elements.accountFormMessage.classList.add("success");
    elements.accountFormMessage.hidden = false;
    elements.createAccountForm.reset();
    await loadAccounts();
  } catch (error) {
    elements.accountFormMessage.textContent = error.message;
    elements.accountFormMessage.classList.remove("success");
    elements.accountFormMessage.hidden = false;
  } finally {
    elements.createAccountButton.disabled = false;
  }
}

function renderAccounts(users) {
  elements.accountList.replaceChildren();
  if (!users.length) {
    const empty = document.createElement("p");
    empty.className = "account-list-empty";
    empty.textContent = "No accounts found.";
    elements.accountList.append(empty);
    return;
  }

  for (const user of users) {
    const item = document.createElement("div");
    item.className = "account-list-item";
    const details = document.createElement("div");
    details.className = "account-list-details";
    const email = document.createElement("strong");
    email.textContent = user.email;
    const created = document.createElement("span");
    created.textContent = `Added ${new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
    }).format(new Date(user.created_at))}`;
    details.append(email, created);
    const role = document.createElement("span");
    role.className = `account-role${user.role === "admin" ? " admin" : ""}`;
    role.textContent = user.role === "admin" ? "Admin" : "User";
    item.append(details, role);
    elements.accountList.append(item);
  }
}

async function loadAccounts() {
  elements.refreshAccountsButton.disabled = true;
  try {
    const result = await requestJson("/api/admin/users");
    renderAccounts(result.users);
  } catch (error) {
    const message = document.createElement("p");
    message.className = "account-list-empty account-list-error";
    message.textContent = error.message;
    elements.accountList.replaceChildren(message);
  } finally {
    elements.refreshAccountsButton.disabled = false;
  }
}

async function initializeAuth() {
  try {
    const result = await requestJson("/api/auth/me");
    showWorkspace(result.user);
    try {
      await loadDatasets();
    } catch (error) {
      setApiStatus(false);
      showNotice(error.message);
    }
  } catch (error) {
    if (error.status === 401) {
      showAuthScreen();
      return;
    }
    setApiStatus(false);
    showAuthScreen(error.message);
  }
}

elements.loginForm.addEventListener("submit", signIn);
elements.resetHelpToggle.addEventListener("click", () => {
  const expanded = elements.resetHelpToggle.getAttribute("aria-expanded") === "true";
  elements.resetHelpToggle.setAttribute("aria-expanded", String(!expanded));
  elements.resetHelp.hidden = expanded;
});
elements.manageAccountsButton.addEventListener("click", () => {
  elements.accountFormMessage.hidden = true;
  elements.accountDialog.showModal();
  loadAccounts();
  elements.newAccountEmail.focus();
});
elements.createAccountForm.addEventListener("submit", createAccount);
elements.refreshAccountsButton.addEventListener("click", loadAccounts);
document.querySelector("#change-password-button").addEventListener("click", () => {
  elements.passwordFormMessage.hidden = true;
  elements.passwordDialog.showModal();
  elements.currentPassword.focus();
});
elements.changePasswordForm.addEventListener("submit", changePassword);
document.querySelector("#rename-dataset-button").addEventListener("click", () => {
  const dataset = state.datasets.find((item) => item.dataset_id === state.activeId);
  if (!dataset) return;
  elements.datasetFilename.value =
    state.displayNames.get(dataset.dataset_id) || dataset.filename;
  elements.renameMessage.hidden = true;
  elements.renameDialog.showModal();
  elements.datasetFilename.focus();
  elements.datasetFilename.select();
});
elements.renameForm.addEventListener("submit", renameDataset);
document.querySelector("#close-rename-dialog").addEventListener("click", closeRenameDialog);
document.querySelector("#cancel-rename-dialog").addEventListener("click", closeRenameDialog);
elements.renameDialog.addEventListener("click", (event) => {
  if (event.target === elements.renameDialog) closeRenameDialog();
});
document.querySelector("#close-password-dialog").addEventListener("click", closePasswordDialog);
document.querySelector("#cancel-password-dialog").addEventListener("click", closePasswordDialog);
elements.passwordDialog.addEventListener("click", (event) => {
  if (event.target === elements.passwordDialog) closePasswordDialog();
});
document.querySelector("#close-account-dialog").addEventListener("click", closeAccountDialog);
document.querySelector("#cancel-account-dialog").addEventListener("click", closeAccountDialog);
elements.accountDialog.addEventListener("click", (event) => {
  if (event.target === elements.accountDialog) closeAccountDialog();
});
document.querySelector("#logout-button").addEventListener("click", signOut);
document.querySelector("#header-upload").addEventListener("click", openFilePicker);
document.querySelector("#empty-upload").addEventListener("click", openFilePicker);
document.querySelector("#browse-button").addEventListener("click", (event) => {
  event.stopPropagation();
  openFilePicker();
});
elements.dropZone.addEventListener("click", (event) => {
  if (event.target !== document.querySelector("#browse-button")) openFilePicker();
});
elements.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openFilePicker();
  }
});
elements.fileInput.addEventListener("change", () => uploadFile(elements.fileInput.files[0]));
elements.dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  elements.dropZone.classList.add("dragging");
});
elements.dropZone.addEventListener("dragleave", () => {
  elements.dropZone.classList.remove("dragging");
});
elements.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  elements.dropZone.classList.remove("dragging");
  uploadFile(event.dataTransfer.files[0]);
});
document.querySelector("#column-search").addEventListener("input", renderColumns);
document.querySelector("#delete-dataset").addEventListener("click", deleteActiveDataset);
document.querySelector("#clean-export-button").addEventListener("click", downloadCleanedDataset);
document.querySelector("#preview-previous").addEventListener("click", () => {
  changePreviewPage(Math.max(0, state.previewOffset - state.previewPageSize));
});
document.querySelector("#preview-next").addEventListener("click", () => {
  changePreviewPage(state.previewOffset + state.previewPageSize);
});
elements.mobileDatasetSelect.addEventListener("change", (event) => {
  selectDataset(event.target.value);
});
elements.profileTab.addEventListener("click", () => {
  elements.profileTab.classList.add("active");
  elements.previewTab.classList.remove("active");
  elements.profileTab.setAttribute("aria-selected", "true");
  elements.previewTab.setAttribute("aria-selected", "false");
  elements.qualityView.hidden = false;
  elements.previewView.hidden = true;
});
elements.previewTab.addEventListener("click", () => {
  elements.previewTab.classList.add("active");
  elements.profileTab.classList.remove("active");
  elements.previewTab.setAttribute("aria-selected", "true");
  elements.profileTab.setAttribute("aria-selected", "false");
  elements.qualityView.hidden = true;
  elements.previewView.hidden = false;
});

initializeAuth();
