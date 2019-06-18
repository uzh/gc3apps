cores <- 8

# Store missing dependencies inside the project folder 
libpath <- "../lib/R/"

# Install missing dependencies
dependencies <- c("foreach", "doParallel", "multtest", "gplots", "LDheatmap", "genetics", "ape", "EMMREML", "compiler", "scatterplot3d")

for (i in dependencies) {
	if(!require(i, character.only=TRUE)) {
		if(!require(i, lib.loc=libpath, character.only=TRUE)) {
			BiocManager::install(i, lib=libpath)
		}
	}
}

# Import GAPIT source files
source("http://www.zzlab.net/GAPIT/emma.txt")
source(paste(libpath, "gapit_functions.R", sep=""))

# Import phenotype and population structure files
y <- read.table("../data/phenotype_data/Mt_Hg_Cd_phenotypes2018.txt", head=TRUE)
cv <- read.table("../data/population_structure/GH2_structure.txt", head=TRUE)

cl <- makeCluster(cores)
registerDoParallel(cl)

foreach (i=1:8) %dopar% {
	# Load dependencies for each parallel instance
	for (j in dependencies) {
		if(!require(j, character.only=TRUE)) {
			require(j, lib.loc=libpath, character.only=TRUE)
		}
	}

	# Load chromosome data
	g <- read.table(paste("../data/snp_data/chr", i, ".hmp.txt", sep=''), head=FALSE)

	# Run GAPIT
	outdir_chr <- paste(../output/01_gwas/chr", i, sep='')
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
