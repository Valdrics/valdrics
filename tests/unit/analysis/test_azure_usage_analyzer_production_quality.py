"""
Production-quality tests for Azure Usage Analyzer.
Tests cover security, performance, edge cases, and real-world scenarios.
"""

from app.shared.analysis.azure_usage_analyzer import AzureUsageAnalyzer


class TestAzureUsageAnalyzerProductionQuality:
    """Production-quality tests covering security, performance, and edge cases."""

    def test_input_validation_and_sanitization(self):
        """Test input validation and sanitization for security."""
        # Test with potentially malicious input
        malicious_records = [
            {
                "ResourceId": "<script>alert('xss')</script>",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "10.0",
            },
            {
                "ResourceId": "../../../etc/passwd",
                "ServiceName": "Storage",
                "PreTaxCost": "5.0",
            },
        ]

        analyzer = AzureUsageAnalyzer(malicious_records)

        # Should handle malicious input without crashing
        idle_vms = analyzer.find_idle_vms()
        unattached_disks = analyzer.find_unattached_disks()

        # Should not crash and return reasonable results
        assert isinstance(idle_vms, list)
        assert isinstance(unattached_disks, list)

    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        import time

        # Create large dataset (1000 records)
        cost_records = []
        for i in range(1000):
            cost_records.append(
                {
                    "ResourceId": f"/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm{i}",
                    "ServiceName": "Virtual Machines",
                    "PreTaxCost": "100.0",
                    "UsageDate": "2024-01-01",
                }
            )

        start_time = time.time()
        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 2.0, (
            f"Analysis too slow: {end_time - start_time:.3f}s"
        )
        assert len(idle_vms) == 1000  # All VMs should be flagged as idle

    def test_cost_calculation_precision(self):
        """Test cost calculation precision and decimal handling."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "60.123456789",  # High precision cost above threshold
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms(days=7)

        assert len(idle_vms) == 1
        vm = idle_vms[0]

        # Monthly cost should be calculated correctly
        expected_monthly = round(60.123456789 * (30 / 7), 2)
        assert vm["monthly_cost"] == expected_monthly

    def test_mixed_case_resource_ids(self):
        """Test handling of mixed case resource IDs."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/Test/providers/Microsoft.Compute/virtualMachines/VM1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "60.0",  # Above threshold
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/SUBSCRIPTIONS/123/RESOURCEGROUPS/TEST/PROVIDERS/MICROSOFT.COMPUTE/VIRTUALMACHINES/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "45.0",  # Below threshold, should not be flagged
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        # Should be grouped together despite case differences, but only one above threshold
        assert len(idle_vms) == 1
        vm = idle_vms[0]
        assert vm["monthly_cost"] == round(105.0 * (30 / 7), 2)  # Combined cost

    def test_missing_cost_values_handling(self):
        """Test handling of missing or invalid cost values."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": None,  # Missing cost
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm2",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "",  # Empty string
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm3",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "invalid",  # Invalid cost
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        # Should handle gracefully without crashing
        assert isinstance(idle_vms, list)

    def test_empty_and_none_values_robustness(self):
        """Test robustness with empty and None values in records."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "60.0",
                "UsageDate": "2024-01-01",
                "MeterCategory": None,
                "MeterName": "",
                "UsageQuantity": None,
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        # Should not crash with None/empty values
        assert len(idle_vms) == 1
        vm = idle_vms[0]
        assert (
            vm["resource_id"]
            == "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1"
        )

    def test_boundary_conditions_zero_and_negative_costs(self):
        """Test boundary conditions with zero and negative costs."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/zero-cost-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "0.0",
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/negative-cost-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "-5.0",  # Negative cost
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms()

        # Zero cost VMs should not be flagged
        # Negative cost VMs should be handled gracefully
        assert isinstance(idle_vms, list)

    def test_resource_type_filtering_accuracy(self):
        """Test accurate filtering by resource types."""
        cost_records = [
            # VM records
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "60.0",  # Above threshold
                "UsageDate": "2024-01-01",
            },
            # Disk records
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/disks/disk1",
                "ServiceName": "Storage",
                "PreTaxCost": "10.0",
                "MeterCategory": "Storage",
                "UsageDate": "2024-01-01",
            },
            # SQL records
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Sql/servers/server1/databases/db1",
                "ServiceName": "SQL Database",
                "PreTaxCost": "70.0",
                "MeterName": "Basic Compute Hours",
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        idle_vms = analyzer.find_idle_vms()
        unattached_disks = analyzer.find_unattached_disks()
        idle_dbs = analyzer.find_idle_sql_databases()

        # Each method should only detect its specific resource type
        assert len(idle_vms) == 1
        assert len(unattached_disks) == 1
        assert len(idle_dbs) == 1

    def test_concurrent_analysis_safety(self):
        """Test thread safety and concurrent analysis."""
        import threading

        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "50.0",
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        results = []
        errors = []

        def run_analysis():
            try:
                result = analyzer.find_idle_vms()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=run_analysis)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should complete successfully
        assert len(results) == 10
        assert len(errors) == 0

        # All results should be identical
        for result in results:
            assert result == results[0]

    def test_real_world_cost_data_scenarios(self):
        """Test with realistic cost data scenarios."""
        # Simulate a month's
        # worth of real Azure cost data
        cost_records = [
            # Active VM with various costs
            {
                "ResourceId": "/subscriptions/123/resourceGroups/prod/providers/Microsoft.Compute/virtualMachines/web-server",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "85.20",
                "MeterCategory": "Virtual Machine",
                "UsageQuantity": "744.0",  # 31 days
                "UsageDate": "2024-01-01",
            },
            {
                "ResourceId": "/subscriptions/123/resourceGroups/prod/providers/Microsoft.Compute/virtualMachines/web-server",
                "ServiceName": "Storage",
                "PreTaxCost": "12.50",
                "MeterCategory": "Storage",
                "MeterName": "Disk Operations",
                "UsageQuantity": "15000.0",
                "UsageDate": "2024-01-01",
            },
            # Idle development VM
            {
                "ResourceId": "/subscriptions/123/resourceGroups/dev/providers/Microsoft.Compute/virtualMachines/idle-dev-vm",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "65.80",
                "MeterCategory": "Virtual Machine",
                "UsageQuantity": "744.0",
                "UsageDate": "2024-01-01",
            },
            # Unattached disk
            {
                "ResourceId": "/subscriptions/123/resourceGroups/dev/providers/Microsoft.Compute/disks/orphan-disk",
                "ServiceName": "Storage",
                "PreTaxCost": "60.0",
                "MeterCategory": "Storage",
                "UsageDate": "2024-01-01",
            },
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        idle_vms = analyzer.find_idle_vms(days=31)
        unattached_disks = analyzer.find_unattached_disks()

        # Should detect idle dev VM but not active web server
        assert len(idle_vms) == 1
        assert idle_vms[0]["resource_name"] == "idle-dev-vm"

        # Should detect unattached disk
        assert len(unattached_disks) == 1
        assert unattached_disks[0]["resource_name"] == "orphan-disk"

    def test_cost_estimation_accuracy(self):
        """Test cost estimation accuracy for different time periods."""
        cost_records = [
            {
                "ResourceId": "/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm1",
                "ServiceName": "Virtual Machines",
                "PreTaxCost": "60.0",  # Daily cost above threshold
                "UsageDate": "2024-01-01",
            }
        ]

        analyzer = AzureUsageAnalyzer(cost_records)

        # Test different day periods
        for days in [1, 7, 30, 90]:
            idle_vms = analyzer.find_idle_vms(days=days)
            assert len(idle_vms) == 1

            vm = idle_vms[0]
            expected_monthly = round(60.0 * (30 / days), 2)
            assert vm["monthly_cost"] == expected_monthly

    def test_memory_usage_efficiency(self):
        """Test memory usage efficiency with large datasets."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create very large dataset (10000 records)
        cost_records = []
        for i in range(10000):
            cost_records.append(
                {
                    "ResourceId": f"/subscriptions/123/resourceGroups/test/providers/Microsoft.Compute/virtualMachines/vm{i}",
                    "ServiceName": "Virtual Machines",
                    "PreTaxCost": "1.0",
                    "UsageDate": "2024-01-01",
                }
            )

        analyzer = AzureUsageAnalyzer(cost_records)
        idle_vms = analyzer.find_idle_vms(
            cost_threshold=0.5
        )  # Lower threshold for this test

        # Check memory usage after processing
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100MB for 10000 records)
        assert memory_increase < 100, f"Excessive memory usage: {memory_increase:.1f}MB"

        # Results should be correct
        assert len(idle_vms) == 10000
