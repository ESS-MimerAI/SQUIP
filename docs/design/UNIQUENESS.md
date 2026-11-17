The pipeline part of SQUIP has substantial precedent.
However, the planned mapping amino-acid profiles → S(q,ω) has already been covered to some extent.

1. MD → S(q,ω)/F(q,t) for QENS: This is a mature ecosystem: 
   - built-in modules in GROMACS and LAMMPS, 
   - nMoldyn,
   - pynamic-structure-factor
   - [MDANSE](https://github.com/ISISNeutronMuon/MDANSE) (ISIS): computes neutron scattering observables from MD trajectories, with instrument-resolution convolution ("virtual experiments"). Standard tool for GROMACS→QENS use case. 
   - [Sassena](https://github.com/benlabs/sassena): C++/MPI, optimized for petascale parallel computation of X-ray and neutron scattering from very large MD trajectories. 
   - [LiquidLib](https://github.com/Z-Laboratory/LiquidLib): computes intermediate scattering functions and van Hove functions with element-specific coherent/incoherent neutron weighting for direct comparison to experiment. 

   We chose [Dynasor](https://gitlab.com/materials-modeling/dynasor) but we need to consider that SQUIP's custom neutron-weighting and validation scripts partially reimplement what MDANSE already ships.
   Dynasor's distinctive combination lies in being able to evaluate static and dynamic structure factors, current correlations, spectral energy density, and mode-projection autocorrelation functions.
   The differences are architectural rather than capability: Dynasor is a pure Python API; MDANSE is GUI-assisted script generation with built-in instrument-resolution convolution. The reason to use Dynasor is squarely due to its Python interface, which composes better with our proposed TaskBlaster automation.
   

2. QENS+MD of small peptides/amino acids in water: well covered. Examples:
    - QENS on H/D-substituted aqueous glycine solutions extracting translational diffusion coefficients and residence times of glycine and water separately [Yoshida et al.](https://pubmed.ncbi.nlm.nih.gov/30278668/);
    - QENS on NAGMA/NALMA model-peptide solutions analyzing water dynamics via the elastic incoherent structure factor [Russo, Head-Gordon et al.](https://pubs.acs.org/jpcbfk/article/109/26/12966/3573503/Molecular-View-of-Water-Dynamics-near-Model).
    - Classic MD work: Tarek & Tobias, and the Kneller/Smith lineage that motivated nMoldyn in the first place.
    
    SQUIP's linewidth→diffusion-coefficient extraction is the textbook jump-diffusion analysis these papers do.

3. The ML extension: This is the novel aspect. Three adjacent projects exist:
    - MLIP-driven neutron prediction workflows. ORNL has an established workflow training ML force fields that reproduce INS spectra at near-DFT accuracy, orders of magnitude faster, and a 2025 workflow paper combines DFT, MLIPs, MD, and autocorrelation analysis to simulate INS, explicitly noting extendability to quasi-elastic scattering. 
    https://www.ornl.gov/research-highlight/machine-learning-force-fields-neutron-scattering-data-analysis

    - Direct structure→spectrum surrogates. Cheng et al. predict 1D and 2D INS spectra directly from atomic coordinates using symmetry-aware networks plus autoencoders trained on a large synthetic INS database. That's the closest analog to SQUIP's "estimate S(q,ω) from a profile" idea, but for crystals/vibrational INS, not QENS of solvated peptides. https://iopscience.iop.org/article/10.1088/2632-2153/acb315

    - Neural representations of S(Q,ω) for parameter inference, e.g. neural implicit representations of the dynamical structure factor fit to inelastic scattering data via automatic differentiation. This is, however, demonstrated so far on spin systems only. https://www.nature.com/articles/s41467-023-41378-4


The novelty of SQUIP lies in pre-trained database for predicting QENS-regime S(q,ω)/F(q,t) of aqueous amino acids/peptides as a function of composition, water model, and temperature. Nobody has done it for the quasi-elastic/diffusive regime of biomolecular solutions. The QENS lineshape is smoother than INS spectra, so a surrogate is easier here.