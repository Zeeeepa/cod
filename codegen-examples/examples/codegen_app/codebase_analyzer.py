#!/usr/bin/env python3
"""
Codebase Analyzer Module

This module provides advanced codebase analysis capabilities for the Coder Agent,
enabling comprehensive examination of code structure, dependencies, and quality.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field

from codegen import Codebase
from codegen.extensions.index.file_index import FileIndex
from codegen.extensions.index.symbol_index import SymbolIndex
from codegen.extensions.index.fcode_index import FCodeIndex

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of codebase analysis that can be performed."""
    DEPENDENCY_GRAPH = "dependency_graph"
    COMPONENT_INTERACTION = "component_interaction"
    TECHNICAL_DEBT = "technical_debt"
    CYCLOMATIC_COMPLEXITY = "cyclomatic_complexity"
    LIBRARY_OPTIMIZATION = "library_optimization"
    ARCHITECTURE_PATTERNS = "architecture_patterns"
    FULL_ANALYSIS = "full_analysis"

@dataclass
class AnalysisResult:
    """Results of a codebase analysis."""
    analysis_type: AnalysisType
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

class CodebaseAnalyzer:
    """
    Advanced codebase analysis tool that provides comprehensive examination
    of code structure, dependencies, and quality.
    
    This class enables:
    - Dependency graph construction
    - Component interaction modeling
    - Technical debt quantification
    - Cyclomatic complexity measurement
    - Library optimization assessment
    - Architecture pattern identification
    """
    
    def __init__(self, codebase: Codebase):
        """
        Initialize the codebase analyzer.
        
        Args:
            codebase: The codebase to analyze
        """
        self.codebase = codebase
        self.file_index = FileIndex(codebase)
        self.symbol_index = SymbolIndex(codebase)
        self.fcode_index = FCodeIndex(codebase)
        
        # Cache for analysis results
        self.analysis_cache: Dict[str, AnalysisResult] = {}
        
        logger.info(f"CodebaseAnalyzer initialized for {codebase.repo_path}")
    
    def analyze(self, analysis_type: Union[AnalysisType, str], force_refresh: bool = False) -> AnalysisResult:
        """
        Perform a specific type of codebase analysis.
        
        Args:
            analysis_type: The type of analysis to perform
            force_refresh: Whether to force a refresh of cached results
            
        Returns:
            The analysis result
        """
        # Convert string to enum if needed
        if isinstance(analysis_type, str):
            try:
                analysis_type = AnalysisType(analysis_type.lower())
            except ValueError:
                raise ValueError(f"Invalid analysis type: {analysis_type}. Must be one of {[t.value for t in AnalysisType]}")
        
        # Check cache unless force_refresh is True
        cache_key = analysis_type.value
        if not force_refresh and cache_key in self.analysis_cache:
            logger.info(f"Using cached analysis result for {analysis_type.value}")
            return self.analysis_cache[cache_key]
        
        # Perform the requested analysis
        logger.info(f"Performing {analysis_type.value} analysis")
        
        if analysis_type == AnalysisType.DEPENDENCY_GRAPH:
            result = self._analyze_dependency_graph()
        elif analysis_type == AnalysisType.COMPONENT_INTERACTION:
            result = self._analyze_component_interaction()
        elif analysis_type == AnalysisType.TECHNICAL_DEBT:
            result = self._analyze_technical_debt()
        elif analysis_type == AnalysisType.CYCLOMATIC_COMPLEXITY:
            result = self._analyze_cyclomatic_complexity()
        elif analysis_type == AnalysisType.LIBRARY_OPTIMIZATION:
            result = self._analyze_library_optimization()
        elif analysis_type == AnalysisType.ARCHITECTURE_PATTERNS:
            result = self._analyze_architecture_patterns()
        elif analysis_type == AnalysisType.FULL_ANALYSIS:
            result = self._perform_full_analysis()
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
        
        # Cache the result
        self.analysis_cache[cache_key] = result
        
        return result
    
    def _analyze_dependency_graph(self) -> AnalysisResult:
        """
        Analyze the dependency graph of the codebase.
        
        Returns:
            Analysis result with dependency graph information
        """
        logger.info("Analyzing dependency graph")
        
        # Collect all symbols and their dependencies
        symbols = self.symbol_index.get_all_symbols()
        dependencies = {}
        
        for symbol in symbols:
            symbol_deps = self.symbol_index.get_symbol_dependencies(symbol.name, symbol.filepath)
            dependencies[f"{symbol.filepath}:{symbol.name}"] = [
                f"{dep.filepath}:{dep.name}" for dep in symbol_deps
            ]
        
        # Identify highly connected components
        connection_counts = {}
        for symbol, deps in dependencies.items():
            connection_counts[symbol] = len(deps)
            for dep in deps:
                if dep not in connection_counts:
                    connection_counts[dep] = 0
                connection_counts[dep] += 1
        
        # Sort by connection count
        sorted_connections = sorted(
            connection_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Generate recommendations
        recommendations = []
        for symbol, count in sorted_connections[:5]:
            if count > 10:
                recommendations.append(
                    f"Consider refactoring {symbol} which has {count} connections"
                )
        
        return AnalysisResult(
            analysis_type=AnalysisType.DEPENDENCY_GRAPH,
            summary=f"Analyzed dependency graph with {len(symbols)} symbols and {sum(len(deps) for deps in dependencies.values())} dependencies",
            details={
                "dependencies": dependencies,
                "highly_connected": sorted_connections[:10]
            },
            metrics={
                "symbol_count": len(symbols),
                "dependency_count": sum(len(deps) for deps in dependencies.values()),
                "avg_dependencies_per_symbol": sum(len(deps) for deps in dependencies.values()) / max(1, len(symbols))
            },
            recommendations=recommendations
        )
    
    def _analyze_component_interaction(self) -> AnalysisResult:
        """
        Analyze component interactions in the codebase.
        
        Returns:
            Analysis result with component interaction information
        """
        logger.info("Analyzing component interactions")
        
        # Identify components (directories with multiple files)
        directories = {}
        for file in self.codebase.files:
            dir_path = os.path.dirname(file.filepath)
            if dir_path not in directories:
                directories[dir_path] = []
            directories[dir_path].append(file.filepath)
        
        # Filter to directories with multiple files
        components = {dir_path: files for dir_path, files in directories.items() if len(files) > 1}
        
        # Analyze interactions between components
        interactions = {}
        for comp1, files1 in components.items():
            interactions[comp1] = {}
            for comp2, files2 in components.items():
                if comp1 != comp2:
                    interaction_count = 0
                    for file1 in files1:
                        for file2 in files2:
                            # Check if file1 imports from file2
                            file1_obj = self.codebase.get_file(file1)
                            for imp in file1_obj.imports:
                                if file2 in imp.source:
                                    interaction_count += 1
                    
                    if interaction_count > 0:
                        interactions[comp1][comp2] = interaction_count
        
        # Generate recommendations
        recommendations = []
        for comp, deps in interactions.items():
            if len(deps) > 5:
                recommendations.append(
                    f"Component {comp} interacts with {len(deps)} other components. Consider reducing coupling."
                )
        
        return AnalysisResult(
            analysis_type=AnalysisType.COMPONENT_INTERACTION,
            summary=f"Analyzed interactions between {len(components)} components",
            details={
                "components": components,
                "interactions": interactions
            },
            metrics={
                "component_count": len(components),
                "interaction_count": sum(len(deps) for deps in interactions.values()),
                "avg_interactions_per_component": sum(len(deps) for deps in interactions.values()) / max(1, len(components))
            },
            recommendations=recommendations
        )
    
    def _analyze_technical_debt(self) -> AnalysisResult:
        """
        Analyze technical debt in the codebase.
        
        Returns:
            Analysis result with technical debt information
        """
        # Implementation details for technical debt analysis
        # This would include code quality metrics, TODO/FIXME counts, etc.
        return AnalysisResult(
            analysis_type=AnalysisType.TECHNICAL_DEBT,
            summary="Technical debt analysis placeholder",
            details={},
            metrics={},
            recommendations=[]
        )
    
    def _analyze_cyclomatic_complexity(self) -> AnalysisResult:
        """
        Analyze cyclomatic complexity in the codebase.
        
        Returns:
            Analysis result with cyclomatic complexity information
        """
        # Implementation details for cyclomatic complexity analysis
        return AnalysisResult(
            analysis_type=AnalysisType.CYCLOMATIC_COMPLEXITY,
            summary="Cyclomatic complexity analysis placeholder",
            details={},
            metrics={},
            recommendations=[]
        )
    
    def _analyze_library_optimization(self) -> AnalysisResult:
        """
        Analyze library usage and optimization opportunities.
        
        Returns:
            Analysis result with library optimization information
        """
        # Implementation details for library optimization analysis
        return AnalysisResult(
            analysis_type=AnalysisType.LIBRARY_OPTIMIZATION,
            summary="Library optimization analysis placeholder",
            details={},
            metrics={},
            recommendations=[]
        )
    
    def _analyze_architecture_patterns(self) -> AnalysisResult:
        """
        Analyze architecture patterns in the codebase.
        
        Returns:
            Analysis result with architecture pattern information
        """
        # Implementation details for architecture pattern analysis
        return AnalysisResult(
            analysis_type=AnalysisType.ARCHITECTURE_PATTERNS,
            summary="Architecture pattern analysis placeholder",
            details={},
            metrics={},
            recommendations=[]
        )
    
    def _perform_full_analysis(self) -> AnalysisResult:
        """
        Perform a full analysis of the codebase.
        
        Returns:
            Comprehensive analysis result
        """
        logger.info("Performing full codebase analysis")
        
        # Perform all individual analyses
        dependency_graph = self._analyze_dependency_graph()
        component_interaction = self._analyze_component_interaction()
        technical_debt = self._analyze_technical_debt()
        cyclomatic_complexity = self._analyze_cyclomatic_complexity()
        library_optimization = self._analyze_library_optimization()
        architecture_patterns = self._analyze_architecture_patterns()
        
        # Combine all recommendations
        all_recommendations = []
        all_recommendations.extend(dependency_graph.recommendations)
        all_recommendations.extend(component_interaction.recommendations)
        all_recommendations.extend(technical_debt.recommendations)
        all_recommendations.extend(cyclomatic_complexity.recommendations)
        all_recommendations.extend(library_optimization.recommendations)
        all_recommendations.extend(architecture_patterns.recommendations)
        
        # Create a comprehensive summary
        summary = (
            f"Full codebase analysis completed with {len(all_recommendations)} recommendations. "
            f"Analyzed {dependency_graph.metrics.get('symbol_count', 0)} symbols and "
            f"{component_interaction.metrics.get('component_count', 0)} components."
        )
        
        return AnalysisResult(
            analysis_type=AnalysisType.FULL_ANALYSIS,
            summary=summary,
            details={
                "dependency_graph": dependency_graph.details,
                "component_interaction": component_interaction.details,
                "technical_debt": technical_debt.details,
                "cyclomatic_complexity": cyclomatic_complexity.details,
                "library_optimization": library_optimization.details,
                "architecture_patterns": architecture_patterns.details
            },
            metrics={
                "dependency_graph": dependency_graph.metrics,
                "component_interaction": component_interaction.metrics,
                "technical_debt": technical_debt.metrics,
                "cyclomatic_complexity": cyclomatic_complexity.metrics,
                "library_optimization": library_optimization.metrics,
                "architecture_patterns": architecture_patterns.metrics
            },
            recommendations=all_recommendations
        )

# Example usage
if __name__ == "__main__":
    from codegen import Codebase
    
    # Initialize a codebase
    codebase = Codebase(repo="Zeeeepa/cod")
    
    # Create an analyzer
    analyzer = CodebaseAnalyzer(codebase)
    
    # Perform a full analysis
    result = analyzer.analyze(AnalysisType.FULL_ANALYSIS)
    
    # Print the summary and recommendations
    print(f"Analysis Summary: {result.summary}")
    print("\nRecommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"{i}. {rec}")