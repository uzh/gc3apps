args <- commandArgs(trailingOnly = TRUE)

if(length(args)!=4){
    print("Usage: R CMD BATCH '--args <functions+script.R> <function_name> <input.ncdf> <result folder>")
    quit(status=1)
}
	
phenotypes_folder = args[1]
chromosomes_folder = args[2]
scripts_folder = args[3]
output_folder = args[4]


# Import
library("parallel")
library("doParallel")
library('foreach')
library('multtest')
library('gplots')
library('LDheatmap')
library('genetics')
library('ape')
library('EMMREML')
library('scatterplot3d')
library("data.table")
library("pryr")

message("DEBUG: Getting phenotype, structure and chromosomes files... ")
phenotype_file <- file.path(phenotypes_folder, dir(phenotypes_folder, pattern = "phenotypes"))
structure_file <- file.path(phenotypes_folder, dir(phenotypes_folder, pattern = "structure"))
chromosomes_files <- file.path(chromosomes_folder, dir(chromosomes_folder, pattern = ".txt"))

# Consistency checks
# 1. check phenotype_file is indeed unique
if (length(phenotype_file) > 1 || length(phenotype_file) == 0) {
   write("Error. phenotype_file should be a single file, found [",length(phenotype_file),"].", stderr())
   quit(save="no", status=1)			      
}

# 2. check structure_file is indeed unique
if (length(structure_file) > 1 || length(structure_file) == 0) {
   write("Error. structure_file should be a single file, found [",length(structure_file),"].", stderr())
   quit(save="no", status=1)			      
}

message("DEBUG: Import GAPIT source files")
# Import GAPIT source files
source("http://www.zzlab.net/GAPIT/emma.txt")
source(file.path(scripts_folder,"gapit_functions.R"))

message("DEBUG: Import phenotype and population structure files")
# Import phenotype and population structure files
y <- read.table(phenotype_file, head=TRUE)
cv <- read.table(structure_file, head=TRUE)

# cores <- parallel::detectCores()
# cl <-parallel::makeCluster(cores, type="SOCK")
# doParallel::registerDoParallel(cl)
# message("DEBUG: detected available cores: ",cores)

foreach (i=1:length(chromosomes_files)) %do%
	# Why do we need to load data.table library again ?
	library("data.table")

	# Load chromosome data
	# g <- read.table(paste("../data/snp_data/chr", i, ".hmp.txt", sep=''), head=FALSE)
	# g <- fread(file.path(chromosomes_folder,paste("chr", 1, ".hmp.txt", sep='')), header=FALSE)
	chromosome = chromosomes_files[i]
	message("DEBUG: reading ",chromosome)
	g <- fread(chromosome, header=FALSE)

	# outdir_chr <- paste(output_folder, "01_gwas/chr", i, sep='')
	outdir_chr <- file.path(output_folder, paste("01_gwas/chr", i, sep = ""))
	message("DEBUG: set working dir to ", outdir_chr)
	dir.create(outdir_chr, showWarnings = TRUE, recursive = FALSE, mode = "0777")
	setwd(paste(outdir_chr))

	# Run GAPIT
	tic("DEBUG: running GAPIT")
	GAPIT(Y=y,			#This is phenotype data
	      G=g,			#This is genotype data, set it to NULL with multiple genotype files
	      CV=cv,			#This is the covariate variables of fixed effects, such as population structure
	      #KI=ki,			#This is kinship data, set it to NULL in case that geneotype files are used for estimation
	      PCA.total = 3,
	      SNP.MAF = 0.02,
	      SNP.fraction=0.6,
	      SNP.impute="Minor",
	      file.Ext.G="hmp.txt",
	      file.from=1,
	      file.to=1,
	      file.fragment = 128,
	      Major.allele.zero=TRUE,
	      Geno.View.output=FALSE
	)

	# cleanup of output folder	

	toc(msg=mem_used())

# stopCluster(cl)


message("Done")
