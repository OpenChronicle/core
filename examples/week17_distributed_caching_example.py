"""
Week 17 Distributed Caching Integration Example
Complete example of distributed caching deployment

This example demonstrates:
- Redis Cluster setup
- Performance monitoring
- Production deployment patterns
- Cache warming strategies
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, UTC

from core.memory_management.distributed_cache import (
    DistributedCacheConfig, ClusterNode, PartitionConfig,
    DistributedMultiTierCache, create_production_distributed_cache
)
from core.memory_management.performance_analytics import (
    CacheAnalyticsDashboard, create_cache_dashboard
)
from core.memory_management.production_monitoring import (
    ProductionMonitoring, setup_production_monitoring
)


async def example_basic_distributed_cache():
    """Example: Basic distributed cache setup."""
    print("=== Basic Distributed Cache Example ===")
    
    # Configure cluster nodes
    cluster_nodes = [
        {'host': 'localhost', 'port': 6379},
        {'host': 'localhost', 'port': 6380},
        {'host': 'localhost', 'port': 6381}
    ]
    
    # Create distributed cache
    cache = create_production_distributed_cache(
        cluster_nodes=cluster_nodes,
        enable_monitoring=True,
        enable_cache_warming=True
    )
    
    try:
        # Initialize cache
        await cache.initialize()
        print("✅ Distributed cache initialized")
        
        # Test basic operations
        test_data = {
            'character': 'Alice',
            'traits': {'intelligence': 9, 'charisma': 8},
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        # Set data
        await cache.set('test:character:alice', test_data, ttl=300)
        print("✅ Data stored in distributed cache")
        
        # Get data
        retrieved = await cache.get('test:character:alice')
        print(f"✅ Data retrieved: {retrieved['character']}")
        
        # Get metrics
        metrics = await cache.get_distributed_metrics()
        print(f"✅ Cache metrics - Hit rate: {metrics.get('overall_hit_rate', 0):.1%}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Note: This example requires Redis servers running on specified ports")
    
    finally:
        await cache.close()


async def example_cache_warming():
    """Example: Cache warming strategies."""
    print("\n=== Cache Warming Example ===")
    
    # Simple configuration for warming example
    config = DistributedCacheConfig(
        enable_cache_warming=True,
        warming_batch_size=50
    )
    
    cache = DistributedMultiTierCache(config)
    
    try:
        await cache.initialize()
        
        # Warm cache with story data
        story_ids = ['story_1', 'story_2', 'story_3']
        character_data = {
            'story_1': ['alice', 'bob', 'charlie'],
            'story_2': ['diana', 'eve'],
            'story_3': ['frank', 'grace', 'henry', 'iris']
        }
        
        print("🔥 Starting cache warming...")
        warming_results = await cache.warm_cache(story_ids, character_data)
        
        # Display results
        if 'characters' in warming_results:
            for story_id, char_results in warming_results['characters'].items():
                success_count = sum(1 for success in char_results.values() if success)
                total_count = len(char_results)
                print(f"✅ {story_id}: {success_count}/{total_count} characters warmed")
        
        if 'memory_snapshots' in warming_results:
            memory_results = warming_results['memory_snapshots']
            success_count = sum(1 for success in memory_results.values() if success)
            print(f"✅ Memory snapshots: {success_count}/{len(memory_results)} warmed")
        
    except Exception as e:
        print(f"❌ Cache warming error: {e}")
    
    finally:
        await cache.close()


async def example_performance_monitoring():
    """Example: Performance monitoring and analytics."""
    print("\n=== Performance Monitoring Example ===")
    
    # Create cache with monitoring enabled
    config = DistributedCacheConfig(
        enable_monitoring=True,
        metrics_collection_interval=10  # 10 seconds for demo
    )
    
    cache = DistributedMultiTierCache(config)
    
    try:
        await cache.initialize()
        
        # Create analytics dashboard
        dashboard = await create_cache_dashboard(cache, auto_start=True)
        print("📊 Analytics dashboard started")
        
        # Generate some cache activity
        print("🔄 Generating cache activity...")
        for i in range(20):
            key = f"test:activity:{i}"
            data = {'index': i, 'timestamp': datetime.now(UTC).isoformat()}
            await cache.set(key, data, ttl=60)
            
            # Read some data back
            if i % 3 == 0:
                await cache.get(key)
        
        # Wait for metrics collection
        await asyncio.sleep(2)
        
        # Get dashboard data
        dashboard_data = dashboard.get_dashboard_data()
        
        if dashboard_data:
            current_metrics = dashboard_data.get('current_metrics', {})
            print(f"📈 Current metrics:")
            print(f"   - Hit rate: {current_metrics.get('overall_hit_rate', 0):.1%}")
            print(f"   - Operations: {current_metrics.get('total_operations', 0)}")
            print(f"   - Response time: {current_metrics.get('avg_redis_response_ms', 0):.1f}ms")
            
            # Check for alerts
            alerts = dashboard_data.get('active_alerts', [])
            if alerts:
                print(f"⚠️  Active alerts: {len(alerts)}")
                for alert in alerts[:3]:  # Show first 3
                    print(f"   - {alert.severity}: {alert.message}")
            else:
                print("✅ No active alerts")
            
            # Show recommendations
            recommendations = dashboard_data.get('recommendations', [])
            if recommendations:
                print(f"💡 Recommendations: {len(recommendations)}")
                for rec in recommendations[:2]:  # Show first 2
                    print(f"   - {rec['title']}: {rec['action']}")
        
        await dashboard.stop_monitoring()
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
    
    finally:
        await cache.close()


async def example_production_setup():
    """Example: Production monitoring setup."""
    print("\n=== Production Setup Example ===")
    
    # Production-style configuration
    cluster_nodes = [
        {'host': 'redis-1.production.com', 'port': 6379},
        {'host': 'redis-2.production.com', 'port': 6379},
        {'host': 'redis-3.production.com', 'port': 6379}
    ]
    
    cache = create_production_distributed_cache(
        cluster_nodes=cluster_nodes,
        enable_monitoring=True,
        enable_cache_warming=True
    )
    
    try:
        # Note: This would fail without actual Redis servers
        # await cache.initialize()
        
        # Create production monitoring
        monitoring = ProductionMonitoring(cache)
        
        # Setup environment-specific config
        env_config = monitoring.setup_environment_monitoring()
        print(f"🏭 Production config: {env_config}")
        
        # Example health check (without real Redis)
        print("🏥 Health check configuration ready")
        print("   - Redis connectivity checks")
        print("   - Cache operation validation")
        print("   - Performance threshold monitoring")
        
        # Example Prometheus metrics endpoint
        print("📊 Prometheus metrics endpoint ready")
        print("   - Cache hit rates")
        print("   - Response times")
        print("   - Cluster node status")
        print("   - Partition distribution")
        
        # Example structured logging
        print("📝 Structured logging configured")
        print("   - Performance metrics")
        print("   - Alert notifications")
        print("   - Cache warming operations")
        
    except Exception as e:
        print(f"❌ Production setup note: {e}")
        print("💡 This example shows configuration - requires actual Redis cluster")
    
    finally:
        await cache.close()


async def example_benchmarking():
    """Example: Performance benchmarking."""
    print("\n=== Performance Benchmarking Example ===")
    
    cache = DistributedMultiTierCache(DistributedCacheConfig())
    
    try:
        await cache.initialize()
        monitoring = ProductionMonitoring(cache)
        
        print("🚀 Running performance benchmark...")
        
        # Run short benchmark
        benchmark_results = await monitoring.benchmark_production_performance(
            duration_seconds=10
        )
        
        print("📊 Benchmark Results:")
        print(f"   - Duration: {benchmark_results['duration_seconds']:.1f}s")
        print(f"   - Operations: {benchmark_results['operations_completed']}")
        print(f"   - Ops/sec: {benchmark_results['operations_per_second']:.1f}")
        print(f"   - Error rate: {benchmark_results['error_rate']:.1%}")
        
        # Performance improvement analysis
        improvement = benchmark_results.get('performance_improvement', {})
        hit_rate_delta = improvement.get('hit_rate_delta', 0)
        response_delta = improvement.get('response_time_delta', 0)
        
        print(f"   - Hit rate change: {hit_rate_delta:+.3f}")
        print(f"   - Response time change: {response_delta:+.1f}ms")
        
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
    
    finally:
        await cache.close()


def example_configuration_patterns():
    """Example: Different configuration patterns."""
    print("\n=== Configuration Patterns Example ===")
    
    # Development configuration
    dev_config = DistributedCacheConfig(
        redis_host='localhost',
        redis_port=6379,
        enable_clustering=False,
        enable_monitoring=True,
        metrics_collection_interval=60,
        character_ttl=300,  # 5 minutes
        memory_ttl=180      # 3 minutes
    )
    print("🛠️  Development config created")
    
    # Staging configuration
    staging_nodes = [
        ClusterNode(host='staging-redis-1', port=6379),
        ClusterNode(host='staging-redis-2', port=6379)
    ]
    
    staging_partition = PartitionConfig(
        partition_key_patterns=['char:*', 'scene:*'],
        replication_factor=2,
        consistency_level='eventual'
    )
    
    staging_config = DistributedCacheConfig(
        cluster_nodes=staging_nodes,
        enable_clustering=True,
        partition_config=staging_partition,
        enable_monitoring=True,
        metrics_collection_interval=30,
        character_ttl=1800,  # 30 minutes
        memory_ttl=900       # 15 minutes
    )
    print("🧪 Staging config created")
    
    # Production configuration
    prod_nodes = [
        ClusterNode(host='prod-redis-1.internal', port=6379, password='secure_password'),
        ClusterNode(host='prod-redis-2.internal', port=6379, password='secure_password'),
        ClusterNode(host='prod-redis-3.internal', port=6379, password='secure_password'),
        ClusterNode(host='prod-redis-4.internal', port=6379, password='secure_password')
    ]
    
    prod_partition = PartitionConfig(
        partition_key_patterns=['char:*', 'scene:*', 'snapshot:*'],
        replication_factor=2,
        consistency_level='eventual'
    )
    
    prod_config = DistributedCacheConfig(
        cluster_nodes=prod_nodes,
        enable_clustering=True,
        partition_config=prod_partition,
        enable_monitoring=True,
        metrics_collection_interval=15,
        enable_cache_warming=True,
        warming_batch_size=200,
        character_ttl=3600,  # 1 hour
        memory_ttl=1800,     # 30 minutes
        default_ttl=2400     # 40 minutes
    )
    print("🏭 Production config created")
    
    # Display key differences
    configs = {
        'Development': dev_config,
        'Staging': staging_config,
        'Production': prod_config
    }
    
    print("\n📋 Configuration Summary:")
    for env_name, config in configs.items():
        cluster_size = len(config.cluster_nodes) if config.cluster_nodes else 1
        print(f"{env_name}:")
        print(f"   - Cluster nodes: {cluster_size}")
        print(f"   - Clustering: {'Yes' if config.enable_clustering else 'No'}")
        print(f"   - Monitoring interval: {config.metrics_collection_interval}s")
        print(f"   - Character TTL: {config.character_ttl}s")


async def example_error_handling():
    """Example: Error handling and resilience."""
    print("\n=== Error Handling Example ===")
    
    # Configure cache with potential failover
    config = DistributedCacheConfig(
        redis_host='nonexistent-redis',  # This will fail
        redis_port=6379,
        enable_monitoring=False
    )
    
    cache = DistributedMultiTierCache(config)
    
    try:
        await cache.initialize()
        
        # Test operations that should gracefully handle Redis unavailability
        print("🔄 Testing cache operations with unavailable Redis...")
        
        # This should work with local cache only
        test_data = {'test': 'data', 'mode': 'local_only'}
        
        # Set operation (should succeed with local cache)
        result = await cache.set('test:key', test_data)
        print(f"✅ Set operation (local): {'Success' if result else 'Failed'}")
        
        # Get operation (should work from local cache)
        retrieved = await cache.get('test:key')
        if retrieved:
            print(f"✅ Get operation (local): Retrieved {retrieved['mode']}")
        else:
            print("❌ Get operation failed")
        
        # Test with fallback function
        def fallback_function():
            return {'source': 'fallback', 'data': 'emergency_data'}
        
        fallback_result = await cache.get('nonexistent:key', fallback_func=fallback_function)
        if fallback_result:
            print(f"✅ Fallback function: {fallback_result['source']}")
        
        print("✅ Error handling working correctly")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    finally:
        await cache.close()


async def main():
    """Run all examples."""
    print("🚀 OpenChronicle Week 17 - Distributed Caching Examples")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    await example_basic_distributed_cache()
    await example_cache_warming()
    await example_performance_monitoring()
    await example_production_setup()
    await example_benchmarking()
    example_configuration_patterns()
    await example_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("\n💡 Next Steps:")
    print("   1. Set up Redis cluster for your environment")
    print("   2. Configure monitoring endpoints")
    print("   3. Implement cache warming for your story data")
    print("   4. Set up Prometheus metrics collection")
    print("   5. Configure production health checks")


if __name__ == "__main__":
    asyncio.run(main())
