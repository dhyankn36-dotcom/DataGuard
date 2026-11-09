const state = {
  datasets: [],
  activeId: null,
  profile: null,
  columns: [],
};

const elements = {
  fileInput: document.querySelector("#file-input"),
  dropZone: document.querySelector("#drop-zone"),
  uploadProgress: document.querySelector("#upload-progress"),
  uploadMessage: document.querySelector("#upload-message"),
  notice: document.querySelector("#notice"),
  datasetList: document.querySelector("#dataset-list"),
  datasetCount: document.querySelector("#dataset-count"),
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

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(result.detail || `Request failed (${response.status}).`);
  }
  return result;
}

async function loadDatasets(selectId) {
  const result = await requestJson("/api/datasets");
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

  if (!state.datasets.length) {
    const empty = document.createElement("p");
    empty.className = "sidebar-empty";
    empty.textContent = "Your datasets will appear here.";
    elements.datasetList.append(empty);
    return;
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
    name.textContent = dataset.filename;
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
  state.activeId = datasetId;
  clearNotice();
  elements.emptyState.hidden = true;
  elements.dashboard.hidden = false;
  renderDatasetList();

  try {
    const result = await requestJson(`/api/datasets/${encodeURIComponent(datasetId)}/profile`);
    state.profile = result.profile;
    state.columns = Object.entries(result.profile.columns).map(([name, details]) => ({
      name,
      ...details,
    }));
    renderProfile(result.filename);
    await renderPreview();
  } catch (error) {
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
    completenessWrap.append(track, percentage);
    completenessCell.append(completenessWrap);
    const uniqueCell = document.createElement("td");
    uniqueCell.textContent = formatNumber(column.unique_values);
    const duplicateCell = document.createElement("td");
    duplicateCell.textContent = formatNumber(column.duplicate_values);
    row.append(nameCell, typeCell, completenessCell, uniqueCell, duplicateCell);
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
  if (!dataset || !window.confirm(`Delete "${dataset.filename}"? This cannot be undone.`)) {
    return;
  }

  clearNotice();
  try {
    await requestJson(`/api/datasets/${encodeURIComponent(dataset.dataset_id)}`, {
      method: "DELETE",
    });
    state.activeId = null;
    await loadDatasets();
    showNotice(`${dataset.filename} was deleted.`, true);
  } catch (error) {
    showNotice(error.message);
  }
}

async function renderPreview() {
  const result = await requestJson(
    `/api/datasets/${encodeURIComponent(state.activeId)}/preview?limit=100`,
  );
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
    `Showing ${formatNumber(result.rows.length)} of ${formatNumber(state.profile.total_rows)} rows.`;
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

loadDatasets().catch((error) => showNotice(error.message));
