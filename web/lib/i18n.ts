import type { Lang, UIDictionary, UILabels } from "@/lib/types";

const EN: UILabels = {
  appTitle: "History Map",
  appSubtitle: "Atlas of Time",
  searchPlaceholder: "Search places, empires, civilizations",
  searchPlaceholderCompact: "Search History Map",
  territories: "Territories",
  civilizations: "Civilizations",
  events: "Events",
  loading: "Loading atlas…",
  error: "The atlas data could not be loaded.",
  retry: "Try again",
  jumpToYear: "Jump to year",
  paused: "Paused",
  playing: "Playing",
  dragHint: "Drag to travel through time",
  play: "Play",
  pause: "Pause",
  legend: "Territories",
  approximate: "Approximate / disputed",
  sources: "Sources & map confidence",
  sourcesShort: "Sources",
  confidence: "Confidence",
  period: "Period",
  observed: "Snapshots",
  type: "Type",
  historical: "Historical",
  contemporary: "Contemporary",
  approximateNote:
    "Dashed edges indicate approximate or contested control. Boundaries are a schematic reconstruction, not exact survey lines.",
  boundaryModernNote:
    "Boundaries are georeferenced to Natural Earth 1:10m and follow modern sovereign outlines.",
  noDescription: "No encyclopedic summary is available for this entity yet.",
  loadingRecord: "Loading record…",
  wikipedia: "Wikipedia",
  wikidata: "Wikidata",
  noResults: "No matches found",
  eventsTitle: "Historical events",
  eventsHint: "Jump to a recorded snapshot",
  close: "Close",
  resetView: "Reset view",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  layers: "Layers",
  labels: "Labels",
  borders: "Borders",
  graticule: "Graticule",
  theme: "Toggle theme",
  language: "Language",
  attribution: "Natural Earth · Historical Basemaps",
  regional: "Regional view",
  approximateShort: "Approximate reconstruction",
  schematicExtent: "Schematic extent",
  featureCount: "polities",
  event: "Event",
  snapshot: "Snapshot",
  layerNote: "Nearest available snapshot",
  names: "Also known as",
  confidenceBasis: "Confidence basis",
  boundary: "Boundary",
  boundaryApproximate: "Approximate reconstruction",
  boundaryApproximateShort: "Approximate borders",
  boundaryGeoreferenced: "Georeferenced",
  openSource: "Open source record",
  showMore: "Details",
  showLess: "Collapse",
  ancient: "Ancient",
  modern: "Modern",
  allSnapshots: "snapshots",
  noSelection: "Select a territory on the map",
  noSelectionHint: "Click a coloured region to read its record.",
  zoomHint: "Scroll to zoom · drag to pan",
  dataSources: "Data sources",
  record: "Record",
  status: "Status",
  externalLinks: "External records",
  confidenceHigh: "High",
  confidenceMedium: "Medium",
  confidenceLow: "Low",
  founded: "From",
  dissolved: "To",
  stepMode: "Step",
  step100y: "100y",
  step10y: "10y",
  step1y: "1y",
  stepMonth: "Month",
  prevStep: "Previous step",
  nextStep: "Next step",
  currentLocation: "Current location",
  historicalPeriods: "Historical Periods",
  periodsSuffix: "periods",
  timeRangePresent: "3000 BCE – present",
  present: "Present"
};

const VI: UILabels = {
  appTitle: "History Map",
  appSubtitle: "Atlas of Time",
  searchPlaceholder: "Tìm địa danh, đế quốc, văn minh",
  searchPlaceholderCompact: "Tìm trong History Map",
  territories: "Lãnh thổ",
  civilizations: "Văn minh",
  events: "Sự kiện",
  loading: "Đang nạp bản đồ…",
  error: "Không thể nạp dữ liệu bản đồ.",
  retry: "Thử lại",
  jumpToYear: "Tới năm",
  paused: "Tạm dừng",
  playing: "Đang phát",
  dragHint: "Kéo để du hành thời gian",
  play: "Phát",
  pause: "Tạm dừng",
  legend: "Lãnh thổ",
  approximate: "Ước lệ / tranh chấp",
  sources: "Nguồn & độ tin cậy bản đồ",
  sourcesShort: "Nguồn",
  confidence: "Độ tin cậy",
  period: "Thời kỳ",
  observed: "Mốc dữ liệu",
  type: "Loại",
  historical: "Lịch sử",
  contemporary: "Đương đại",
  approximateNote:
    "Nét đứt biểu thị quyền kiểm soát ước lệ hoặc tranh chấp. Ranh giới là bản tái dựng sơ lược, không phải đường khảo sát chính xác.",
  boundaryModernNote:
    "Ranh giới được định vị theo Natural Earth 1:10m và bám theo đường biên quốc gia hiện đại.",
  noDescription: "Chưa có mô tả bách khoa cho thực thể này.",
  loadingRecord: "Đang nạp hồ sơ…",
  wikipedia: "Wikipedia",
  wikidata: "Wikidata",
  noResults: "Không tìm thấy kết quả",
  eventsTitle: "Sự kiện lịch sử",
  eventsHint: "Chuyển tới một mốc dữ liệu",
  close: "Đóng",
  resetView: "Về khung mặc định",
  zoomIn: "Phóng to",
  zoomOut: "Thu nhỏ",
  layers: "Lớp bản đồ",
  labels: "Nhãn",
  borders: "Đường biên",
  graticule: "Kinh vĩ tuyến",
  theme: "Đổi giao diện",
  language: "Ngôn ngữ",
  attribution: "Natural Earth · Historical Basemaps",
  regional: "Góc nhìn khu vực",
  approximateShort: "Tái dựng ước lệ",
  schematicExtent: "Phạm vi sơ lược",
  featureCount: "thực thể",
  event: "Sự kiện",
  snapshot: "Mốc",
  layerNote: "Mốc dữ liệu gần nhất",
  names: "Tên khác",
  confidenceBasis: "Cơ sở độ tin cậy",
  boundary: "Ranh giới",
  boundaryApproximate: "Tái dựng ước lệ",
  boundaryApproximateShort: "Ranh giới ước lệ",
  boundaryGeoreferenced: "Đã định vị địa lý",
  openSource: "Hồ sơ nguồn mở",
  showMore: "Chi tiết",
  showLess: "Thu gọn",
  ancient: "Cổ đại",
  modern: "Cận đại",
  allSnapshots: "mốc",
  noSelection: "Chọn một lãnh thổ trên bản đồ",
  noSelectionHint: "Nhấp vào vùng màu để xem hồ sơ.",
  zoomHint: "Cuộn để phóng · kéo để di chuyển",
  dataSources: "Nguồn dữ liệu",
  record: "Hồ sơ",
  status: "Trạng thái",
  externalLinks: "Hồ sơ ngoài",
  confidenceHigh: "Cao",
  confidenceMedium: "Trung bình",
  confidenceLow: "Thấp",
  founded: "Từ",
  dissolved: "Đến",
  stepMode: "Bước",
  step100y: "100y",
  step10y: "10y",
  step1y: "1y",
  stepMonth: "Tháng",
  prevStep: "Lùi một bước",
  nextStep: "Tiến một bước",
  currentLocation: "Vị trí hiện tại",
  historicalPeriods: "Phân kỳ lịch sử",
  periodsSuffix: "thời kỳ",
  timeRangePresent: "3000 TCN – nay",
  present: "Hiện tại"
};

export const UI: Record<string, UILabels> = { en: EN, vi: VI };

export interface LanguageOption {
  code: string;
  label: string;
  badge: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: "en", label: "English", badge: "EN" },
  { code: "vi", label: "Tiếng Việt", badge: "VI" }
];

export const MONTH_NAMES_EN = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
] as const;

export interface LocaleFormat {
  code: string;
  bceSuffix: string;
  ceSuffix: string;
  presentLabel: string;
  formatMonthYear: (month: number, yearFormatted: string) => string;
  formatFullDate: (day: number, month: number, yearFormatted: string) => string;
  wikiPrefix: string;
}

// extensible locale formatting rules for calendar dates and era names
export const LOCALES: Record<string, LocaleFormat> = {
  en: {
    code: "en",
    bceSuffix: "BC",
    ceSuffix: "AD",
    presentLabel: "Present",
    formatMonthYear: (m, y) => `${MONTH_NAMES_EN[m - 1]} ${y}`,
    formatFullDate: (d, m, y) => `${MONTH_NAMES_EN[m - 1]} ${d}, ${y}`,
    wikiPrefix: "en"
  },
  vi: {
    code: "vi",
    bceSuffix: "TCN",
    ceSuffix: "SCN",
    presentLabel: "Hiện tại",
    formatMonthYear: (m, y) => `Tháng ${m}, ${y}`,
    formatFullDate: (d, m, y) => `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${y}`,
    wikiPrefix: "vi"
  }
};

export function getLocale(lang?: string): LocaleFormat {
  if (!lang) return LOCALES.en;
  return LOCALES[lang] || LOCALES.en;
}

export const TYPE_LABELS: Record<string, Record<string, string>> = {
  en: {
    empire: "Empire",
    kingdom: "Kingdom",
    republic: "Republic",
    civilization: "Civilization",
    city_state: "City-state",
    protectorate: "Protectorate",
    colony: "Colony",
    federation: "Federation",
    state: "State",
    dependent_territory: "Dependent territory",
    disputed_territory: "Disputed territory"
  },
  vi: {
    empire: "Đế quốc",
    kingdom: "Vương quốc",
    republic: "Cộng hòa",
    civilization: "Văn minh",
    city_state: "Thành bang",
    protectorate: "Bảo hộ",
    colony: "Thuộc địa",
    federation: "Liên bang",
    state: "Quốc gia",
    dependent_territory: "Lãnh thổ phụ thuộc",
    disputed_territory: "Lãnh thổ tranh chấp"
  }
};

export function getUI(lang?: string): UILabels {
  if (!lang) return UI.en;
  return UI[lang] || UI.en;
}

export function typeLabel(type: string | null | undefined, lang: string = "en") {
  if (!type) return "—";
  return TYPE_LABELS[lang]?.[type] || TYPE_LABELS.en[type] || type || "—";
}

export function getInitialLang(): string {
  if (typeof window === "undefined") return "en";
  const saved = window.localStorage.getItem("hm-lang");
  if (saved && (saved in UI || SUPPORTED_LANGUAGES.some((l) => l.code === saved))) {
    return saved;
  }
  return "en";
}
