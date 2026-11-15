# Web scraping con R para toda Bolivia: visita los enlaces de backend/data/base.csv
# (áreas protegidas, fauna, flora, ecosistemas, recursos hídricos y conservación) y guarda en
# backend/data/scraped.json el título, la descripción y los primeros párrafos de cada página.
# Instalar: install.packages(c("rvest", "httr", "jsonlite"))   (R >= 4.1)
suppressPackageStartupMessages({ library(rvest); library(httr); library(jsonlite) })

args <- commandArgs(trailingOnly = FALSE)
f <- sub("--file=", "", args[grep("--file=", args)])
dir_data <- normalizePath(file.path(if (length(f)) dirname(normalizePath(f)) else getwd(), "..", "backend", "data"))
salida <- file.path(dir_data, "scraped.json")
base <- read.csv(file.path(dir_data, "base.csv"), encoding = "UTF-8", stringsAsFactors = FALSE)
resultado <- if (file.exists(salida)) fromJSON(salida, simplifyVector = FALSE) else list()

limpiar <- function(x) trimws(gsub("\\s+", " ", gsub("\\[[0-9a-z ]{1,8}\\]", "", x)))

extraer <- function(url) {
  r <- GET(url, timeout(20), user_agent("Mozilla/5.0 EcoBol/1.0 (proyecto academico)"), add_headers(`Accept-Language` = "es"))
  stop_for_status(r)
  pg <- read_html(content(r, "text", encoding = "UTF-8"))
  desc <- pg |> html_element("meta[name='description']") |> html_attr("content")
  titulo <- pg |> html_element("title") |> html_text2()
  p <- limpiar(pg |> html_elements("p") |> html_text2())
  p <- p[nchar(p) > 80 & nchar(p) < 700]
  list(titulo = ifelse(is.na(titulo), "", titulo), descripcion = ifelse(is.na(desc), "", desc),
       parrafos = as.list(head(p, 5)), estado = "ok", actualizado = format(Sys.Date(), "%Y-%m-%d"))
}

for (i in seq_len(nrow(base))) {
  id <- as.character(base$id[i]); url <- base$enlace[i]
  cat(sprintf("[%s/%s] %s ... ", i, nrow(base), base$nombre[i]))
  if (grepl("booking|tripadvisor", url)) { cat("omitido (buscador)\n"); next }  # estos sitios bloquean el scraping
  res <- tryCatch(extraer(url), error = function(e) { cat("error:", conditionMessage(e), "\n"); NULL })
  if (!is.null(res)) { resultado[[id]] <- res; cat("ok\n") }
  Sys.sleep(1.5)
}
write(toJSON(resultado, auto_unbox = TRUE, pretty = TRUE), salida)
cat("Guardado en", salida, "\n")
