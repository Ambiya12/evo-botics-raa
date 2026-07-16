<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        // Frontend compilation is validated by a separate CI job. Feature
        // tests should render Blade views without requiring a Vite manifest.
        $this->withoutVite();
    }
}
