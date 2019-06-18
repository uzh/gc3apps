args <- commandArgs(trailingOnly = TRUE)

# gwas <- function(phenotypes_folder, chromosomes_folder, output_folder) {

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
library('doParallel')
library('multtest')
library('gplots')
library('LDheatmap')
library('genetics')
library('ape')
library('EMMREML')
library('scatterplot3d')

phenotype_file <- dir(phenotypes_folder, pattern = "phenotypes")
structure_file <- dir(phenotypes_folder, pattern = "structure")
chromosomes_files <- dir(chromosomes_folder, pattern = ".txt")

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

# Import GAPIT source files
source("http://www.zzlab.net/GAPIT/emma.txt")
source(file.path(scripts_folder,"gapit_functions.R"))

# Import phenotype and population structure files
y <- read.table(phenotype_file, head=TRUE)
cv <- read.table(structure_file, head=TRUE)

cores <- parallel::detectCores()
cl <-parallel::makeCluster(cores)
doParallel::registerDoParallel(cl)

foreach (i=1:8) %dopar% {
	# Load chromosome data
	# g <- read.table(paste("../data/snp_data/chr", i, ".hmp.txt", sep=''), head=FALSE)
	g <- read.table(paste(chromosomes_folder, i, ".hmp.txt", sep=''), head=FALSE)

	# Run GAPIT
	# outdir_chr <- paste(output_folder, "01_gwas/chr", i, sep='')
	outdir_chr <- file.path(output_folder, paste("01_gwas/chr", i, sep = ""))
	dir.create(outdir_chr)
	setwd(paste(outdir_chr))

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
}
stopCluster(cl)
#}