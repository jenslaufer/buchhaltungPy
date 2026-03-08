# CLI wrapper for R accounting functions
# Usage: Rscript r_wrapper.R <command> <args...>
#
# Commands:
#   betriebsergebnis  <journal> <konten> <start> <ende>
#   koerperschaftssteuer <journal> <konten> <start> <ende>
#   soli              <journal> <konten> <start> <ende>
#   gewerbesteuer     <hebesatz> <journal> <konten> <start> <ende>
#   steuern           <journal> <konten> <start> <ende> <hebesatz>
#   validiere_journal <journal> <konten> <start> <ende>
#   guv               <journal> <konten> <start> <ende> <hebesatz> <output_csv>
#   bilanz            <journal> <konten> <start> <ende> <hebesatz> <output_csv>
#   validiere_bilanz  <journal> <konten> <start> <ende> <hebesatz>
#   konten            <journal> <konten> <start> <ende> <output_csv>
#   jahresabschluss   <journal> <konten> <start> <hebesatz>
#   jahreseroeffnung  <journal> <konten> <ende> <hebesatz>

suppressPackageStartupMessages({
  library(tidyverse)
  library(glue)
  library(lubridate)
  library(uuid)
})

# Source the accounting functions — use commandArgs to find script location
script_path <- commandArgs() %>% str_subset("--file=") %>% str_replace("--file=", "")
script_dir <- dirname(normalizePath(script_path))
r_source <- file.path(script_dir, "..", "..", "buchhaltungR", "R", "buchhaltung.R")
# Set working directory so ../data/ paths resolve correctly
setwd(file.path(script_dir, "..", "..", "buchhaltungR", "notebooks"))
source(r_source)

args <- commandArgs(trailingOnly = TRUE)
command <- args[1]

parse_date <- function(s) as.Date(s, format = "%Y-%m-%d")

result <- tryCatch({
  switch(command,
    "betriebsergebnis" = {
      val <- berechne_betriebsergebnis(args[2], args[3], parse_date(args[4]), parse_date(args[5]))
      cat(format(val, nsmall = 2), "\n")
    },
    "koerperschaftssteuer" = {
      val <- berechne_koerperschaftssteuer(args[2], args[3], parse_date(args[4]), parse_date(args[5]))
      cat(format(val, nsmall = 2), "\n")
    },
    "soli" = {
      val <- berechne_soli(args[2], args[3], parse_date(args[4]), parse_date(args[5]))
      cat(format(val, nsmall = 2), "\n")
    },
    "gewerbesteuer" = {
      val <- berechne_gewerbesteuer(as.numeric(args[2]), args[3], args[4], parse_date(args[5]), parse_date(args[6]))
      cat(format(val, nsmall = 2), "\n")
    },
    "steuern" = {
      val <- steuern(args[2], args[3], parse_date(args[4]), parse_date(args[5]), as.numeric(args[6]))
      cat(format(val, nsmall = 2), "\n")
    },
    "validiere_journal" = {
      val <- validiere_journal(args[2], args[3], parse_date(args[4]), parse_date(args[5]))
      cat(val, "\n")
    },
    "guv" = {
      result <- guv(args[2], args[3], parse_date(args[4]), parse_date(args[5]), as.numeric(args[6]))
      write_csv(result, args[7])
      cat("OK\n")
    },
    "bilanz" = {
      result <- bilanz(args[2], args[3], parse_date(args[4]), parse_date(args[5]), as.numeric(args[6]))
      write_csv(result, args[7])
      cat("OK\n")
    },
    "validiere_bilanz" = {
      b <- bilanz(args[2], args[3], parse_date(args[4]), parse_date(args[5]), as.numeric(args[6]))
      val <- validiere_bilanz(b)
      cat(val, "\n")
    },
    "konten" = {
      result <- .get_konten(args[2], args[3], parse_date(args[4]), parse_date(args[5]), TRUE)
      # Drop the nested data column for CSV export
      result <- result %>% select(-data)
      write_csv(result, args[6])
      cat("OK\n")
    },
    "jahresabschluss" = {
      jahresabschluss(args[2], args[3], parse_date(args[4]), as.numeric(args[5]))
      cat("OK\n")
    },
    "jahreseroeffnung" = {
      jahreseroeffnung(args[2], args[3], parse_date(args[4]), as.numeric(args[5]))
      # R function doesn't return the path, construct it
      new_year <- year(parse_date(args[4])) + 1
      new_file <- str_sub(args[2], 1, -5) %>% str_c(glue("_{new_year}.csv"))
      cat(new_file, "\n")
    },
    stop(paste("Unknown command:", command))
  )
}, error = function(e) {
  cat("ERROR:", conditionMessage(e), "\n", file = stderr())
  quit(status = 1)
})
